# CHANGELOG

全ての注目すべき変更はこのファイルに記録します。フォーマットは「Keep a Changelog」準拠です。

なお本ファイルはコードベースの内容から推測して作成しています（初期公開リリース想定）。

## [0.1.0] - 2026-03-31

### 追加 (Added)
- 初期リリースを追加。
- パッケージ構成を追加:
  - kabusys パッケージのエントリポイントを定義（src/kabusys/__init__.py, __version__ = "0.1.0"）。
  - サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ に公開）。
- 環境設定管理モジュールを追加（src/kabusys/config.py）。
  - .env / .env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - export 付き行やクォート、インラインコメントなどを考慮した .env パーサー実装。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数取得用の _require()、Settings クラスを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）。
  - デフォルト値: KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）など。
- AI 関連モジュール（src/kabusys/ai）を追加:
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）:
    - raw_news / news_symbols を用いて銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を計算。
    - バッチサイズ、チャンクごとのトリム、最大記事数等のトークン肥大化対策を実装。
    - JSON Mode 応答のバリデーション、JSONパース回復ロジック、数値クリップ（±1.0）。
    - リトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実装。
    - テスト容易性のため _call_openai_api をパッチ可能に設計。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出は news_nlp.calc_news_window と連携、OpenAI 呼び出しは独立実装で結合を最小化。
    - API 失敗時は macro_sentiment = 0.0（フェイルセーフ）。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）。
- Research モジュール群（src/kabusys/research）を追加:
  - factor_research.py:
    - モメンタム、バリュー、ボラティリティ（ATR 等）、流動性指標の計算を実装。
    - prices_daily / raw_financials を参照する SQL ベースの実装（DuckDB 用）。
    - 戻り値は (date, code) をキーとする dict のリスト。
  - feature_exploration.py:
    - 将来リターン計算（複数ホライズン対応）、Spearman ランク相関（IC）計算、ランク付けユーティリティ、ファクター統計サマリーを実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - research パッケージの __init__ で主要関数を再公開。
- Data モジュール群（src/kabusys/data）を追加:
  - calendar_management.py:
    - JPX カレンダー（market_calendar）管理、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、夜間バッチ更新ジョブ calendar_update_job 実装。
    - DB 値優先、未登録日は曜日ベースでフォールバック。最大探索範囲制限あり。
    - J-Quants クライアント（jquants_client）経由で差分取得／保存を実行。
  - pipeline.py / etl.py:
    - ETLResult データクラス（取得・保存件数、品質問題、エラー集約）を提供。
    - 差分更新、バックフィル、品質チェックの設計方針を実装（jquants_client と quality を利用）。
    - _get_max_date 等のユーティリティ実装。
  - data パッケージの __init__ / etl で ETLResult を再エクスポート。
- テスト容易性・安全設計:
  - LLM 呼び出し箇所は明示的にパッチ可能（ユニットテスト用に _call_openai_api を差し替え可能）。
  - datetime.today()/date.today() をスコア計算等で直接参照しない実装（ルックアヘッドバイアス回避）。
  - API 呼び出し失敗時のフォールバック（スコア 0.0 やスキップ）を多用し、システムの頑健性を確保。
- ロギングと警告の強化:
  - データ不足、API エラー、パース失敗、ROLLBACK 失敗等に関して詳細な warning/info/log を追加。

### 変更 (Changed)
- 初版のため該当なし（初期追加のみ）。

### 修正 (Fixed)
- 初版のため該当なし。

### セキュリティ (Security)
- 初版のため該当なし。

### 注意事項 / 既知の制約 (Notes / Known limitations)
- 必須環境変数が未設定の場合、Settings プロパティや score_* 関数は ValueError を送出するため、デプロイ前に環境変数を整備する必要があります（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。
- OpenAI のレスポンスは JSON モードを期待しているものの、実環境では余分なテキストが混入する可能性があるため、パース回復ロジックを搭載していますが完全保証はありません。
- DuckDB バインドの仕様差（executemany の空リスト不可、リスト型バインドの互換性等）に対処するため実装がやや冗長になっています。DuckDB の将来バージョンで挙動が変わる可能性があります。
- news_nlp・regime_detector は gpt-4o-mini を想定しているが、モデルや API 仕様変更により調整が必要になる場合があります。
- カレンダー更新ジョブは J-Quants クライアント実装（jquants_client）に依存します。API 呼び出し失敗時は処理をスキップして 0 を返します。

### 開発者向けメモ (For developers)
- .env の自動読み込みはプロジェクトルート検出に __file__ の親階層を用いるため、パッケージ配布後も CWD に依存せず動作する想定です。
- LLM 関連処理はテストで安定させるため、_call_openai_api の差し替えを推奨します（unittest.mock.patch など）。
- DB 書き込みは可能な限り冪等（DELETE→INSERT / ON CONFLICT DO UPDATE）にしてあり、部分失敗時に既存データを不必要に消さない設計になっています。

---

今後のリリースでは以下を検討してください（提案）:
- ai モジュールの結果保存/監査ログ機能の拡充（応答の信頼度やメタデータの保存）。
- モデル切替やローカルベースラインモデルの導入を容易にする抽象化。
- ETL の並列化や進捗監視用のメトリクス出力（Prometheus 等）や Slack 通知の統合強化。