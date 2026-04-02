# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
初回リリース v0.1.0 の機能・設計方針・既知の問題をコードベースから推測して日本語で記載します。

## [0.1.0] - 2026-04-02

### 追加
- パッケージ初期公開
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）
  - 公開サブパッケージ: data, research, ai, execution, strategy, monitoring（__all__ に基づく）

- 環境設定ユーティリティ（src/kabusys/config.py）
  - .env / .env.local 自動ロード機能（プロジェクトルートは .git または pyproject.toml で検出）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - .env パーサーの実装（コメント行、export プレフィックス、クォート内エスケープ、インラインコメントの扱いに対応）
  - OS 環境変数を保護する protected 上書きロジック（.env.local は override）
  - Settings クラスを提供し、環境変数取得をプロパティ経由で行う
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - データベースパス: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - 監視設定: PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
    - システム設定: KABUSYS_ENV（development/paper_trading/live のバリデーション）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
    - is_live / is_paper / is_dev ヘルパー

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を集約して銘柄ごとのニュースを作成
  - OpenAI（gpt-4o-mini）を用いたバッチ分析（1回のバッチ最大 20 銘柄、JSON Mode）
  - タイムウィンドウの計算ユーティリティ calc_news_window（前日15:00 JST ～ 当日08:30 JST を UTC に変換）
  - スコアの検証・正規化（results キーのバリデーション、未知コードは無視、±1.0 にクリップ）
  - 再試行ロジックとエラー時のフォールバック（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）
  - ai_scores テーブルへの冪等的書込み（対象コードのみ DELETE → INSERT）

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定
  - MA 計算は target_date 未満のデータのみ使用（ルックアヘッド防止）
  - マクロニュースは raw_news からマクロキーワードでフィルタし、OpenAI（gpt-4o-mini）でセンチメントを計算
  - API 失敗時は macro_sentiment=0.0 をフォールバック（フェイルセーフ）
  - レジームスコア合成と閾値判定（BULL_THRESHOLD / BEAR_THRESHOLD）
  - market_regime テーブルへの冪等書込み（BEGIN / DELETE / INSERT / COMMIT）

- データプラットフォーム関連（src/kabusys/data/*）
  - カレンダー管理モジュール（calendar_management.py）
    - market_calendar の存在確認、DB優先の営業日判定・フォールバック（DB未登録日は曜日ベース）
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供
    - calendar_update_job により J-Quants から差分取得・バックフィル・保存を行う（_BACKFILL_DAYS、健全性チェック含む）
  - ETL パイプラインインターフェース（etl.py と pipeline.py）
    - ETLResult データクラスを提供（取得件数 / 保存件数 / 品質問題 / エラーの集約）
    - 差分更新、バックフィル、品質チェックを行う設計（jquants_client と quality モジュールを連携）
    - DuckDB を用いた idempotent 保存と互換性配慮（executemany の空リスト対策など）

- 研究・ファクターモジュール（src/kabusys/research/*）
  - factor_research.py
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を prices_daily から算出（200 日データ不足時は None）
    - calc_volatility: 20 日 ATR（atr_20 / atr_pct）および流動性指標（avg_turnover / volume_ratio）を計算
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS=0 は None）
  - feature_exploration.py
    - calc_forward_returns: LEAD を使って将来リターン（デフォルト horizons = [1,5,21]）を算出
    - calc_ic: ファクターと将来リターンのスピアマンランク相関を計算
    - rank: 同順位は平均ランクとするランク付け実装（丸めにより ties の安定化）
    - factor_summary: count/mean/std/min/max/median の統計サマリーを標準ライブラリのみで計算
  - research パッケージは主要関数を外部公開（__all__）

### 変更
- 初回リリースのため、過去の変更履歴はありません。

### 修正
- 初回リリースのため、過去の修正はありません。

### 既知の問題 / 注意点
- OpenAI API キーの扱い
  - news_nlp.score_news および regime_detector.score_regime は api_key 引数を受け取り、未指定時に環境変数 OPENAI_API_KEY を参照します。未設定時は ValueError を送出します。
- フェイルセーフ設計
  - LLM 呼び出し失敗時はスコアを 0.0（中立）にフォールバックするなどの挙動により、ETL/解析処理の継続を優先しています。必要に応じて呼び出し元で失敗判定を行ってください。
- .env 自動ロード
  - 自動ロードはプロジェクトルート探索に基づくため、配布後や環境によっては想定通りに検出されない場合があります。自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB executemany の互換性対策
  - 空の params を executemany へ渡さないガードが入っています（DuckDB 0.10 互換性対応）。
- コード断片（潜在的バグ）
  - src/kabusys/data/pipeline.py の末尾付近が断片的に切れているように見えます（ファイルの最後に "return date.fro" のような不完全な文字列が含まれている）。この部分は意図せぬ切断・タイポの可能性があるため、ビルド/実行前に該当箇所を確認してください。

### セキュリティ
- 機密情報は環境変数から取得する設計（トークン・APIキー・パスワード等）。.env の取り扱いはユーザーに委ねられます。

---

今後のリリースで想定される改善案（参考）
- ETL の完全実装と単体テスト（pipeline モジュールの末尾断片の修正）
- OpenAI からのレスポンス検証の強化とメトリクス出力
- モジュール間の依存分離やインターフェースの明確化（テスト用フックの追加）
- 監視・アラートの実装拡充（Slack 連携の実運用確認）

（以上）