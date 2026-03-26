CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

0.1.0 - 2026-03-26
-----------------

Added
- パッケージ初期リリース（kabusys v0.1.0）。
- パブリック API:
  - パッケージトップでのエクスポートを定義: data, strategy, execution, monitoring。
- 環境設定管理 (kabusys.config):
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD 実装。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォートのエスケープ、インラインコメントの扱いを考慮）。
  - 環境変数保護機構（OS の既存環境変数を protected として上書きを制御）。
  - Settings クラスを導入し、J-Quants / kabuステーション / Slack / DB パス / システム設定（env, log_level）をプロパティとして提供。必須変数は未設定時に ValueError を送出。
  - サポートされる KABUSYS_ENV 値（development, paper_trading, live）とログレベルの検証を追加。
- AI モジュール (kabusys.ai):
  - ニュース NLP スコアリング (news_nlp.score_news):
    - raw_news と news_symbols を元に、前日 15:00 JST ～ 当日 08:30 JST の記事ウィンドウを集約して銘柄別に OpenAI（gpt-4o-mini）でセンチメントを算出。
    - バッチ処理（1 API コールで最大 20 銘柄）／記事数・文字数トリム／レスポンスの厳格なバリデーションを実装。
    - エラー（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフのリトライ、非 5xx やパース失敗時は該当チャンクをスキップするフェイルセーフ。
    - スコアは ±1.0 にクリップ。DuckDB への書き込みは置換（DELETE → INSERT）で冪等性を確保し、部分失敗時に既存スコアを保護。
    - calc_news_window ユーティリティを提供（JST→UTC 変換を含む）。
  - 市場レジーム判定 (ai.regime_detector.score_regime):
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出、OpenAI 呼び出し、スコア合成、閾値判定、market_regime テーブルへの冪等書き込みを実装。
    - OpenAI API 呼び出し失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
  - モジュール内で OpenAI 呼び出し関数をモジュール毎に独立実装（モジュール間でプライベート関数を共有しない設計）。
- Data モジュール (kabusys.data):
  - カレンダー管理 (calendar_management):
    - JPX カレンダーの夜間バッチ更新 calendar_update_job 実装（J-Quants から差分取得、market_calendar へ冪等保存）。
    - 営業日判定ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar が未取得のときは曜日ベース（週末除外）でフォールバックする堅牢な動作。
    - DB に NULL が混入した場合の警告とフォールバック（設計上想定外だが安全に対処）。
    - 最大探索範囲 (_MAX_SEARCH_DAYS) による無限ループ防止等の安全策を導入。
  - ETL パイプライン (pipeline, etl):
    - ETLResult データクラスを実装し ETL の取得/保存件数・品質チェック結果・エラー情報を集約。
    - 差分取得、バックフィル、品質チェック（quality モジュールとの連携）を考慮した ETL 設計を反映。
    - pipeline の ETLResult を etl モジュールから再エクスポート。
- Research モジュール (kabusys.research):
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。欠損取り扱いを考慮。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS が 0/欠損時は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンを一括取得可能な実装。
    - calc_ic: ファクター値と将来リターンのスピアマン IC（ランク相関）を実装（有効レコード < 3 なら None）。
    - rank, factor_summary: ランク化（平均ランクの tie 処理）とファクター統計サマリを提供。
- DuckDB を使用した SQL ベースの処理群を多数実装（prices_daily / raw_news / raw_financials / market_calendar / ai_scores / market_regime などを前提）。

Changed
- なし（初回リリース）。

Fixed
- なし（初回リリース）。

Removed
- なし（初回リリース）。

Security
- なし特記。

Notes / 実装上の重要ポイント
- OpenAI API の扱い:
  - API キーは関数引数で注入可能（テスト容易性）かつ引数未指定時は環境変数 OPENAI_API_KEY を参照。未指定の場合は ValueError。
  - gpt-4o-mini を利用し、JSON Mode（response_format={"type": "json_object"}）で厳密な JSON を期待するが、レスポンス前後の余計なテキストを扱う復元ロジックを実装。
  - モジュール毎に _call_openai_api を独立実装してテスト時に差し替えやすくしている。
- データベース操作:
  - DuckDB への書き込みは明示的な BEGIN / DELETE / INSERT / COMMIT（例外時は ROLLBACK）で冪等性・整合性を重視。
  - DuckDB executemany に空リストを渡せない制約に配慮した保護ロジックを含む。
- 時刻の扱い:
  - すべての処理で datetime.today() / date.today() をむやみに参照しない方針（ルックアヘッドバイアス回避）。target_date を明示的に渡す API を採用。
  - ニュースウィンドウ等では JST と UTC の明示的変換を行っている。
- .env パーサ:
  - export プレフィックス、クォート内のエスケープ、インラインコメントの扱いなど POSIX ライクな .env をかなり robust に処理。

互換性/破壊的変更
- 初回リリースのため互換性周りの履歴はありません。将来的に内部 API を変更する場合は Breaking チェンジとして別途告知予定です。

今後の予定（示唆）
- ai スコアリングやレジーム判定のモデル選択やプロンプトの改善、パフォーマンス計測の追加。
- ETL のスケジューリング / observability 強化（監査ログ、メトリクス）。
- strategy / execution / monitoring パッケージの実装拡張（現在は名前空間として公開）。

----------------------------------------
この CHANGELOG はコードベースから推測して作成しています。実際のリリース作業時は日付・バージョン・リリースノートを実環境に合わせて更新してください。