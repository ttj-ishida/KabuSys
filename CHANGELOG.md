CHANGELOG
=========

このファイルは「Keep a Changelog」形式に準拠しています。  
※リリース日はコードベースから推測して 2026-03-31 としています。必要に応じて修正してください。

フォーマット:
- Unreleased: 次のリリースの変更点を記載
- 各バージョン: 追加 (Added)、変更 (Changed)、修正 (Fixed) 等で分類

Unreleased
----------
（なし）

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ基盤
  - kabusys パッケージ初期版を追加。パッケージバージョンは __version__ = "0.1.0"。
  - パッケージの公開APIとして data / strategy / execution / monitoring をエクスポート。

- 環境設定（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード:
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - 必須設定の取得ヘルパー（_require）を提供。未設定時は ValueError を投げる。
  - 主要設定プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH（デフォルトパスを設定）
    - CPU/MEMORY/DISK の監視閾値（デフォルト値を設定）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/... の検証）

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を読み、銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）に送信してセンチメントを算出し、ai_scores テーブルへ書き込む score_news を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づく記事選定（UTC に変換して DB クエリ）。
    - バッチサイズ、記事数・文字数上限、JSON Mode を用いた厳密な JSON 応答パース。
    - レート制限(429)/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。
    - レスポンス検証（results 配列、code/score の検証、数値チェック）と ±1.0 でのクリップ。
    - DuckDB に対して idempotent に DELETE → INSERT でスコアを書き換える（部分失敗時に既存スコアを保護）。
    - テスト容易性のため _call_openai_api を置換可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を判定する score_regime を実装。
    - ma200_ratio 計算は target_date 未満のデータのみを使用（ルックアヘッドバイアス回避）。
    - マクロニュース抽出はタイトルベースでキーワードフィルタを使用（最大 20 件）。
    - OpenAI 呼び出しはリトライ/バックオフを実装し、API 失敗時は macro_sentiment=0.0 を採用するフェイルセーフ。
    - market_regime テーブルへトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等書き込み。例外時は ROLLBACK を試行。

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを利用した営業日判定ユーティリティ群を提供：
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがない場合は曜日ベース（土日非営業）でフォールバックする設計。
    - next/prev/get_trading_day 系は DB 登録値を優先し、未登録日は曜日判定で補完。探索上限で無限ループ防止。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等更新。バックフィルと健全性チェックを実装。
  - ETL / パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（etl モジュールは pipeline.ETLResult を再エクスポート）。
    - ETL パイプライン方針を定義（差分更新、保存は idempotent、品質チェックを収集して継続する設計）。
    - DuckDB テーブル存在チェック、最大日付取得等のユーティリティを追加（DuckDB 互換性に配慮）。
  - jquants_client 等外部クライアント呼び出しは抽象化して利用（fetch/save の呼び出し箇所あり）。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日MA乖離）を計算。データ不足時は None。
    - calc_volatility: 20 日 ATR, 相対 ATR, 20 日平均売買代金, 出来高比率を計算。欠損ハンドリングあり。
    - calc_value: raw_financials から直近財務を取得して PER, ROE を計算（EPS が 0 または欠損なら PER は None）。
    - すべて DuckDB 内 SQL（窓関数中心）で実装し、外部発注等に影響しない設計。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を使って一括取得。horizons の検証あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 未満の場合は None。
    - rank: 同順位は平均ランクを採るランク関数（丸めで ties 検出を安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計ユーティリティ。
    - 外部ライブラリ非依存（標準ライブラリのみ）で実装。

- 汎用/実装上の注意点（横断的）
  - ルックアヘッドバイアス回避: 各モジュールで datetime.today()/date.today() を直接参照しないよう設計（target_date を明示的引数に取る）。
  - OpenAI 呼び出し:
    - gpt-4o-mini を想定、JSON Mode を利用して厳密な JSON を期待するプロンプト設計。
    - API の失敗ケースでフェイルセーフ（中立スコア）を採用する箇所がある。
    - テストのために _call_openai_api を patch して差し替え可能。
  - データベース操作:
    - DuckDB を前提に実装。executemany の空リスト制約等、特定バージョンの注意点に対処。
    - DB 書き込みはトランザクションで行い、例外時は ROLLBACK を試みる。
  - ロギング: 各モジュールで詳細な debug/info/warning を出力するように実装。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated / Removed / Security
- （初版のため該当なし）

Notes / 要設定環境変数（主なもの）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
  - OPENAI_API_KEY（AI モジュール実行時）
- 任意/デフォルトあり:
  - KABUSYS_ENV（development/paper_trading/live, default=development）
  - LOG_LEVEL（default=INFO）
  - DUCKDB_PATH（default=data/kabusys.duckdb）
  - SQLITE_PATH（default=data/monitoring.db）
  - PID_FILE_PATH（default=data/execution.pid）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1（自動 .env ロード抑止）

今後の検討事項（推奨）
- 単体テスト/統合テストの整備: OpenAI 呼び出しや J-Quants クライアントをモックするテストカバレッジ。
- エラーメトリクス/アラート連携（Slack 等）による運用監視自動化。
- パフォーマンス最適化: ETL の差分算出や DuckDB クエリのインデックス/パーティショニング検討。
- セキュリティ: シークレット管理（Vault 等）導入の検討。

---  
（この CHANGELOG はソースコードからの推測に基づき作成しています。実際の変更履歴や日付は開発プロセスに合わせて調整してください。）