# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
このリポジトリの初期リリースを記録しています。

v0.1.0 — 2026-03-31
-------------------

概要
- 日本株自動売買プラットフォーム「KabuSys」の初期実装を追加しました。
- データ取得・ETL、マーケットカレンダー管理、特徴量（ファクター）計算、ニュースのAI評価、マーケットレジーム判定、環境設定など、コアとなる多くのモジュールを実装しています。

Added
- パッケージ初期設定
  - パッケージメタ情報を追加（kabusys.__init__ に __version__ = "0.1.0"）。
  - パッケージ外部公開モジュール: data, strategy, execution, monitoring（__all__）。

- 環境変数・設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロードを実装（プロジェクトルートの検出は .git または pyproject.toml を基準）。
  - .env / .env.local の優先順序（OS 環境変数 > .env.local > .env）。.env.local は上書き（override=True）される。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト等で利用）。
  - .env パーサ: コメント、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - 上書き保護（protected）を導入し、既存の OS 環境変数を誤って上書きしないように保護。
  - Settings クラスを提供し、主要設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU/MEMORY/DISK 閾値, KABUSYS_ENV, LOG_LEVEL 等）をプロパティで取得。必須変数未設定時は ValueError を送出。
  - デフォルト値：KABU_API_BASE_URL, データファイルパス（data/kabusys.duckdb, data/monitoring.db）等。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（ai_score）を計算する score_news を実装。
  - ニュース収集ウィンドウ（JST 前日 15:00 ～ 当日 08:30）を計算する calc_news_window を実装（内部では UTC naive datetime を返す）。
  - バッチ処理（1回あたり最大 20 銘柄）・トークン肥大化対策（記事件数上限・文字数トリム）・JSON Mode を用いた堅牢なレスポンスパースを実装。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ処理を実装。致命的でないエラーはフェイルセーフ的にスキップし続行。
  - レスポンスのバリデーション（results 配列、code の整合性、数値チェック）・スコアを ±1 にクリップする処理を実装。
  - DuckDB 互換性考慮（executemany に空リストを渡さない等）。

- マーケットレジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を組み合わせて、日次で market_regime テーブルへ書き込む score_regime を実装。
  - ニュース取得は news_nlp.calc_news_window を利用し、マクロキーワードでフィルタ（_MACRO_KEYWORDS）。
  - OpenAI 呼び出しは JSON 出力を期待し、API エラー時は macro_sentiment=0.0 で継続（フェイルセーフ）。
  - ルックアヘッドバイアス対策（date 比較は target_date 未満 / datetime.today() を参照しない）。
  - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。

- データ（kabusys.data）
  - ETL インターフェースのエクスポート（kabusys.data.etl が ETLResult を再エクスポート）。
  - ETL パイプライン（kabusys.data.pipeline）:
    - ETLResult データクラスを追加。品質チェック結果・エラーの集約、has_errors / has_quality_errors / to_dict を提供。
    - 差分取得・バックフィル・品質チェックの設計を反映した骨組みを実装。J-Quants クライアント（jquants_client）を使用する想定。
    - DuckDB テーブル存在チェック・最大日付取得などのユーティリティを実装（DuckDB の制約を考慮）。
  - マーケットカレンダー管理（kabusys.data.calendar_management）:
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - market_calendar が未取得のときは曜日ベース（週末は非営業日）でフォールバックする一貫したロジックを採用。
    - カレンダーの夜間更新ジョブ calendar_update_job を実装（J-Quants から差分取得・バックフィル・健全性チェック）。
    - 最大探索日数・バックフィル日数・先読み日数等の定数を定義。

- 研究・ファクター（kabusys.research）
  - factor_research モジュールを追加（calc_momentum, calc_volatility, calc_value）。
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）。
    - Volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率等（データ不足時は None）。
    - Value: per（株価/EPS）と roe（raw_financials から最新財務を取得）。
    - DuckDB SQL を用いた実装（外部 API へのアクセスなし）。
  - feature_exploration モジュールを追加（calc_forward_returns, calc_ic, factor_summary, rank）。
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。
    - rank / factor_summary: ランク化、統計サマリーを提供。
    - pandas 等に依存しない純 Python 実装。

Design / Implementation notes
- ルックアヘッドバイアス対策
  - 各処理は内部で datetime.today() / date.today() に依存しないよう設計（すべて target_date を明示的に受け取る）。
  - DB クエリでは target_date 未満 / 排他条件を用いることで将来データ参照を防止。

- OpenAI API 利用
  - 使用モデル: gpt-4o-mini（JSON Mode を期待するプロンプト）。
  - レスポンスの頑健なパース（余分な前後テキストの復元含む）。
  - テスト容易性のため、内部の _call_openai_api をモック可能に設計（unittest.mock.patch を想定）。

- トランザクション・冪等性
  - market_regime や ai_scores への書き込みは冪等化（削除→挿入）＋BEGIN/COMMIT/ROLLBACK を利用。
  - DuckDB のバージョン差異（executemany の空リスト扱い等）に配慮した実装。

- エラーハンドリング
  - API エラーやパースエラーは基本的にフェイルセーフにし、可能な限り処理を継続（局所的にスキップ）する方針。
  - 重大な DB 書き込みエラーは上位へ伝播（呼び出し元での取り扱いを想定）。

Security / Ops
- 必須環境変数（例）
  - OPENAI_API_KEY（score_news, score_regime の呼び出しに必要）
  - JQUANTS_REFRESH_TOKEN（J-Quants 関連クライアント）
  - KABU_API_PASSWORD（kabu ステーション API）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（通知）
- .env 自動ロードはデフォルトで有効（プロジェクトルート検出に失敗する場合はスキップ）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

Known limitations / TODOs
- ETL の詳細（jquants_client の実装、quality モジュールの具体チェック）は本コード片では抽象化されている。実際の ETL ワークフローでは jquants_client の実装と品質チェックルールが必要。
- factor_research の一部（PBR・配当利回り）は現バージョンで未実装（calc_value に注記あり）。
- DuckDB の日付型や executemany の挙動はバージョン依存のため、本リリースでは互換性ワークアラウンドを入れているが、将来的な DuckDB バージョンでの再確認が必要。
- OpenAI 呼び出しのコスト・レイテンシー対策（キャッシュやローカルモデルの検討）は今後の検討課題。

Migration notes
- 初回導入時は .env.example を参考に .env を作成し、必要な環境変数を設定してください。
- 自動ロードを無効化したいテストベンチでは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI API を利用する処理を CI でテストする際は、_call_openai_api をモックするか、api_key をテスト用に注入してください。

---

（この CHANGELOG は提供されたコードベースの実装内容から推測して作成しています。実際のリリースノートとして流用する場合は、追加のコンテキストや運用情報を追記してください。）