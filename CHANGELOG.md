# Changelog

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

現在のバージョン: 0.1.0

## [0.1.0] - 2026-04-02
初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化モジュールを追加（kabusys.__init__）。公開モジュール: data, strategy, execution, monitoring。
  - パッケージバージョンを `0.1.0` として定義。

- 設定 / 環境変数管理
  - 環境変数自動読み込み機能を実装（kabusys.config）。
    - プロジェクトルートを `.git` または `pyproject.toml` から検出して `.env` / `.env.local` を自動ロード。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - `.env` のパースはコメント・クォート・`export KEY=val` 形式に対応。
    - `.env.local` は `.env` をオーバーライドする挙動（ただし既存の OS 環境変数は保護）。
  - Settings クラスを実装し、アプリケーション設定をプロパティ経由で提供。
    - J-Quants / kabu API / Slack / DB パス / 監視しきい値 / 環境（development/paper_trading/live）/ログレベルなどを取得。
    - 必須項目（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は未設定時に ValueError を送出。

- AI（自然言語処理）機能
  - ニュースセンチメント分析（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）へバッチ送信し、ai_scores テーブルへ書き込み。
    - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）の計算ユーティリティを提供（calc_news_window）。
    - バッチサイズ、トークン肥大化対策（記事数上限・文字数トリム）、JSON Mode レスポンスのバリデーション、スコアクリップ（±1.0）、エクスポネンシャルバックオフによるリトライを実装。
    - API キーは引数優先、引数が None の場合は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。
    - フェイルセーフ: API失敗やパース失敗はログ出力の上でスキップ（例外を投げず継続）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を組み合わせて日次でレジーム判定（bull/neutral/bear）を行う。
    - DuckDB 上の prices_daily / raw_news を参照して計算。LLM 呼び出しは OpenAI クライアントを使用しリトライ/バックオフを実装。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 失敗時は macro_sentiment を 0.0 とするフェイルセーフを採用。
    - レジーム算出ロジックはルックアヘッドバイアスを防ぐ設計（date 未満条件、datetime.today() を直接参照しない）。

- データプラットフォーム
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを追加して ETL 実行結果（取得数・保存数・品質問題・エラー）を集約。
    - 差分取得・バックフィル・品質チェックの考え方をコードに反映。
  - ETL 便利公開（kabusys.data.etl）で ETLResult を再エクスポート。
  - 市場カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを利用した営業日判定ユーティリティを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫したロジックを採用。
    - calendar_update_job を実装し J-Quants API から差分取得・バックフィルして market_calendar を更新する処理を提供（健全性チェック・バックフィル日数を考慮）。
    - J-Quants クライアント呼び出し部は jquants_client モジュールに委譲（インターフェースを想定）。

- リサーチ・ファクター
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M）、200 日 MA 乖離、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金・出来高比）などのファクターを実装。
    - raw_financials を用いた PER / ROE を計算する calc_value を実装。
    - DuckDB の SQL ウィンドウ関数を活用し、結果を {date, code, ...} の辞書リストで返却。
    - データ不足時の null ハンドリング（None を返す）。
  - 特徴量解析ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト 1,5,21 営業日）に対応。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関を実装。
    - ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas など外部依存を避け、標準ライブラリと DuckDB のみで実装。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- （初回リリースのため該当なし）

### 既知の注意点 / 設計上の考慮
- ルックアヘッドバイアス対策:
  - 多くの処理で datetime.today()/date.today() を直接参照せず、外部から target_date を渡す設計。テスト/検証やバックテストで正確性が保たれるよう配慮。
- OpenAI 絡み:
  - API 呼び出しは gpt-4o-mini を想定。レスポンスの JSON 解析にフォールバックロジック（余分テキストの切り出し）を実装しているが、LLM 出力の多様性には限界があるため、実運用では API レスポンスの監視が推奨される。
  - API キーは関数引数優先、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時に ValueError が発生するためデプロイ前に必ず設定が必要。
- DuckDB 互換性:
  - executemany に空リストを渡せない制約（DuckDB 0.10）に対応するため、空チェックを行っている。
- 環境変数自動読み込み:
  - 自動で .env/.env.local をプロジェクトルートから読み込むが、テストや一時的な環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して無効化可能。

### 必要な環境変数（代表例）
- OPENAI_API_KEY (AI 機能利用時)
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH など（省略時はデフォルトパスを使用）

---

今後の予定（案）
- strategy / execution / monitoring 各モジュールの詳細実装（本リリースではエントリポイントを用意済み）。
- テストカバレッジ拡充（特に OpenAI 周りのモックを利用した回帰テスト）。
- 性能最適化と大規模データに対するメモリ/クエリ改善。

もし特定モジュールについてより詳細な変更点（例: 関数の入出力・例外挙動・API 互換性など）を CHANGELOG に反映したい場合は、対象モジュール名を指定していただければ、さらに項目を分解して追記します。