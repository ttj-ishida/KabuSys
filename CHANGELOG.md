CHANGELOG
=========

すべての注目すべき変更はここに記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。  

0.1.0 - 2026-04-01
------------------

Added
- パッケージ初期リリースとして以下の主要機能を追加しました。
  - 基本パッケージ情報
    - パッケージ名: KabuSys、バージョン: 0.1.0
    - パッケージ公開インターフェースを __all__ で定義（data, strategy, execution, monitoring）。
  - 設定 / 環境変数管理（kabusys.config）
    - .env/.env.local ファイルの自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を起点）。
    - export KEY=val 形式やシングル／ダブルクォート、エスケープ、行末コメント等に対応した独自パーサを実装。
    - OS 環境変数保護（既存環境変数は上書きされない; .env.local は override=True で上書き可）。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を導入（テスト等で利用可能）。
    - 必須環境変数チェック用の _require() と Settings クラスを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）。
    - システム設定（KABUSYS_ENV の検証、LOG_LEVEL 検証）、各種パスや監視閾値（CPU/MEM/DISK）をプロパティとして提供。
  - AI モジュール（kabusys.ai）
    - news_nlp.score_news: ニュース記事を OpenAI（gpt-4o-mini）でセンチメント評価し、ai_scores テーブルへ書き込む。
      - JST ベースのニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。
      - 銘柄ごとに記事を集約し（最大記事数・最大文字数でトリム）、最大 20 銘柄/チャンクでバッチ送信。
      - JSON Mode 応答の堅牢なバリデーション（余分な前後テキストの復元・results フィールド検査・数値検証）。
      - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。API 失敗時は該当チャンクをスキップ（フェイルセーフ）。
      - DuckDB の executemany 空リスト問題への対処（空リストを渡さない条件分岐）。
      - テスト容易性のため _call_openai_api を patch できる設計。
    - regime_detector.score_regime: ETF（1321）200日移動平均乖離とマクロニュース（LLMセンチメント）を合成して日次市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存。
      - ma200_ratio 計算（target_date 未満のデータのみ使用、ルックアヘッド防止）。
      - マクロキーワードによる記事抽出、LLM によるマクロセンチメント評価（JSON 出力期待）。
      - 合成スコアと閾値に基づくラベリング、DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
      - API 失敗・パース失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
      - OpenAI 呼び出しは独立関数化し、news_nlp と共有しない設計。
  - データプラットフォーム（kabusys.data）
    - calendar_management: JPX カレンダーの管理と夜間バッチ更新機能を実装。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の提供。
      - market_calendar がない場合は曜日ベース（週末を休日）でフォールバックする一貫性のある動作。
      - calendar_update_job: J-Quants から差分取得し冪等に保存、バックフィル・健全性チェックを実装。
    - pipeline / etl:
      - ETLResult データクラスを公開（ETL の統計・品質問題・エラーメッセージを集約）。
      - ETL における差分取得、バックフィル、品質チェック（quality モジュールとの連携）に対応する基礎実装。
      - 内部ユーティリティで DuckDB テーブル存在チェックや最大日付取得等を提供。
    - jquants_client などのクライアント群（参照実装を想定）との連携ポイントを用意。
  - 研究用モジュール（kabusys.research）
    - factor_research: momentum / value / volatility / liquidity 等のファクター計算を実装。
      - calc_momentum: 1M/3M/6M リターン、ma200_dev（データ不足時は None）。
      - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等。
      - calc_value: raw_financials から最新財務を取得し PER, ROE を算出。
      - 設計上、本モジュールは prices_daily / raw_financials のみを参照し外部発注や API 呼び出しは行わない。
    - feature_exploration:
      - calc_forward_returns: target_date から複数ホライズン先の将来リターンを計算（ホライズンのバリデーションあり）。
      - calc_ic: Spearman のランク相関（IC）をコード結合して計算（有効レコード 3 未満は None）。
      - rank: 同順位は平均ランクを採る安定なランク関数。
      - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算する統計サマリー。
  - テスト・開発支援
    - OpenAI API 呼び出し箇所に対して patch 可能な内部関数を設置し、ユニットテストでのモックを容易に。
    - 自動 .env 読み込みを無効化する環境変数を用意。

Changed
- 初期リリースにつき、過去バージョンからの変更はありません（新規導入）。

Fixed
- 初期リリースにつき、リリース時点での小さな堅牢化やログ改善を含む実装。

Notes / 設計上の注意点
- ルックアヘッドバイアスを防ぐため、各モジュールは date.today()/datetime.today() を直接参照しない設計です。必ず target_date を呼び出し元から渡してください。
- OpenAI 呼び出しでの失敗時は、LLM 由来の値を中立（0.0）にフォールバックする方針です（フェイルセーフ）。そのため LLM の可用性低下時でも DB 更新が停止しにくい設計になっています。
- DuckDB のバージョン差異（executemany に空リストを渡せない等）に配慮した実装になっています。
- .env パーサは複数のケース（エスケープ、クォート、コメント）に対応していますが、極端に複雑なシンタックスは保証しません。.env.example を参照してください。

Migration / セットアップ注意
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（score_news / score_regime 実行時に必要）
- データベース: DuckDB に prices_daily / raw_news / news_symbols / ai_scores / market_regime / market_calendar / raw_financials 等のスキーマが想定されています。ETL による初期ロードを実行してください。
- テスト時:
  - 自動 .env 読込を抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - OpenAI 呼び出し箇所は unittest.mock.patch で _call_openai_api を差し替えてテスト可能です。

既知の制限 / 今後の改善候補
- LLM のレスポンス仕様依存（JSON mode）: LLM 側の挙動が変わるとパースロジックの調整が必要になります。
- ai スコア・レジーム判定の重みや閾値はハードコードされています。将来的に設定化や学習ベースの最適化を検討。
- ETL / calendar_update_job の J-Quants クライアント呼び出しは外部 API の可用性に依存するため、より詳細な再試行や監査ログの強化が望ましい。

Contributors
- 初期実装: 開発チーム（コードベースからの推測に基づく総称）

ライセンス
- リポジトリに含まれるライセンスに従ってください（この CHANGELOG はドキュメント目的の自動生成物です）。

--- 

（注）本 CHANGELOG は提示されたソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。必要に応じてプロジェクトのコミットログ・リリースポリシーに合わせて調整してください。