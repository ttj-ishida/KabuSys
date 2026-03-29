# CHANGELOG

すべての注記は Keep a Changelog の形式に準拠します。  
このリポジトリの最初の公開リリース（0.1.0）に相当する変更点を、コードベースから推測してまとめています。

全般的な方針・設計上の特徴
- DuckDB を主要なオンディスク分析 DB として利用する設計（prices_daily / raw_news / ai_scores / market_regime / market_calendar / raw_financials 等を想定）。
- 外部 API（J-Quants / OpenAI）との接続を組み込み、失敗に対してフェイルセーフ（スコア 0 やスキップ）を採用。API 呼び出し点はテスト容易性のため差し替え可能に実装。
- ルックアヘッドバイアス防止：date.today()/datetime.today() を直接参照せず、target_date ベースでウィンドウ計算・クエリ制限を行う設計。
- DB 書き込みは冪等性（DELETE→INSERT や ON CONFLICT 想定）を優先。トランザクション（BEGIN/COMMIT/ROLLBACK）で保護。
- .env 自動ロードの仕組みを提供。OS 環境変数は保護して上書きされないよう配慮。自動ロードは環境変数で無効化可能。

[Unreleased]
- （なし）

[0.1.0] - 2026-03-29
Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョン __version__="0.1.0"、公開 API として data/strategy/execution/monitoring を想定してエクスポート。
- 環境設定管理（kabusys.config）
  - .env ファイル（.env / .env.local）および OS 環境変数から設定を読み込む自動ロード機能を実装。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは export プレフィックスやクォート、エスケープ、インラインコメント（スペース直前の # をコメントとみなす）に対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / データベースパス（DuckDB/SQLite）/実行環境（development/paper_trading/live）/ログレベルの取得を容易に。
  - 必須環境変数未設定時に明確なエラーメッセージを出す _require 関数を用意。
- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini、JSON Mode）で銘柄ごとのセンチメント（-1.0〜1.0）を算出、ai_scores テーブルへ書き込む処理を実装。
  - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）計算のユーティリティ（calc_news_window）。
  - バッチ処理（最大20銘柄/チャンク）、1銘柄あたり記事数上限・文字数トリム等のトークン肥大化対策。
  - レスポンスの厳格なバリデーション、JSON の前後ノイズ復元、スコアクリップ、部分書き換え（対象コードのみ DELETE→INSERT）による部分失敗耐性。
  - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装。重大なエラーはスキップして他銘柄の処理を継続するフェイルセーフ設計。
  - テスト用に OpenAI 呼び出しを差し替えられるフック（内部 _call_openai_api）を用意。
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、market_regime テーブルに日次で判定結果（score/label）を書き込む機能を実装。
  - マクロニュース抽出（キーワードリストに基づくタイトルフィルタ）→ OpenAI による -1.0〜1.0 のマクロセンチメント評価 → 合成スコアのクリップとラベリング（bull/neutral/bear）。
  - API 呼び出し失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
  - DuckDB クエリは target_date 未満のみを参照しルックアヘッドを防止。DB へは冪等書き込み（DELETE→INSERT）で安全に更新。
  - OpenAI クライアント作成に api_key 引数または環境変数 OPENAI_API_KEY を利用可能。
- データ関連
  - calendar_management モジュールを追加。market_calendar を基に営業日判定（is_trading_day/is_sq_day）、前後営業日検索（next_trading_day/prev_trading_day）、期間内営業日一覧取得（get_trading_days）などを提供。
  - カレンダー未取得時は曜日ベース（平日）でフォールバックする一貫したロジック。探索上限 (_MAX_SEARCH_DAYS) を設けて無限ループを防止。
  - calendar_update_job を実装し、J-Quants から差分取得して market_calendar を冪等に更新（バックフィル・健全性チェック付き）。
  - data.pipeline に ETLResult データクラスを導入。ETL の実行結果（取得件数・保存件数・品質問題・エラー等）を構造化して返す。
  - data.pipeline で差分更新・バックフィル・品質チェック（quality モジュールを参照）に基づく ETL 処理方針を文書化・実装方針を用意。
  - data.etl モジュールで pipeline.ETLResult を再エクスポート。
- リサーチ機能（kabusys.research）
  - factor_research: Momentum / Volatility / Value 系の定量ファクター計算を実装（mom_1m/3m/6m、ma200_dev、atr_20、atr_pct、avg_turnover、volume_ratio、per、roe 等）。prices_daily / raw_financials を参照。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク化ユーティリティ（rank）を提供。外部依存を持たず標準ライブラリと DuckDB SQL で実装。
- ドキュメント風コメント
  - 各モジュールに処理フロー・設計方針・注意点（例: ルックアヘッド回避、DuckDB executemany の注意）を詳細にコメントとして記載。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- .env 自動読み込みで OS 環境変数を保護（読み込み時に protected set を用いて既存キーを上書きしない挙動をデフォルトに設定）。
- 必須トークンは Settings 経由で取得し、未設定時は ValueError を送出して明確にエラーを示す。

Migration notes / 注意事項
- OpenAI を利用する機能（score_news, score_regime）は OPENAI_API_KEY の設定（あるいは各関数に api_key を渡す）を必須とします。未設定時は ValueError が発生します。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）から行われます。配布環境で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB のテーブルスキーマ（prices_daily / raw_news / news_symbols / ai_scores / market_regime / market_calendar / raw_financials 等）は本コードが期待する形式に合わせる必要があります。ETLResult や各関数の docstring を参照してください。
- OpenAI 呼び出しは JSON Mode（response_format={"type":"json_object"}）を前提に実装しているため、将来的な SDK 変更がある場合はレスポンス処理を見直してください。
- テスト時は内部の _call_openai_api をパッチして API 呼び出しを差し替えられます（unittest.mock.patch の利用を想定）。

既知の制約 / 今後の改善候補（コードから推測）
- 一部 DuckDB バインド（list のバインド等）がバージョン依存のため、実行環境の DuckDB バージョンに注意が必要。executemany の空リスト禁止を考慮したガードを実装済み。
- news_nlp/regime_detector の LLM プロンプトやキーワードリストは将来のチューニング対象。
- 一部機能（Strategy / Execution / Monitoring）はパッケージトップでエクスポート名のみ定義されており、実装は別途追加される想定。

参考: 主要な環境変数
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で利用）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン
- KABU_API_PASSWORD, KABU_API_BASE_URL: kabuステーション連携設定
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知設定
- DUCKDB_PATH, SQLITE_PATH: デフォルトのデータベースファイルパス
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

---

（この CHANGELOG はコード内の docstring・関数署名・設計コメントから推測して作成しています。実際のリリースノートとして利用する場合は、差分や実際の変更履歴に合わせて調整してください。）