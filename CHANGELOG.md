# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

現在のパッケージバージョン: 0.1.0

## [0.1.0] - 2026-03-29

### 追加 (Added)
- パッケージ初回リリース。KabuSys — 日本株自動売買・データ基盤向けユーティリティ群を提供。
- パッケージメタ:
  - バージョン: 0.1.0
  - パッケージエントリポイント: kabusys（__all__ に data, strategy, execution, monitoring を公開）

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイル自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数は保護され上書きされない。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト向け）。
  - .env パーサは以下に対応:
    - 空行 / コメント行（#）無視
    - export KEY=val 形式の取り扱い
    - シングル/ダブルクォート、エスケープシーケンス対応
    - インラインコメントの扱い（クォート有無での挙動を適切に処理）
  - Settings クラスを提供し、必須項目の取得（_require）や値検証を行うプロパティを実装:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得
    - KABUSYS_ENV（development, paper_trading, live）と LOG_LEVEL 値検証
    - データベースパスのデフォルト（duckdb, sqlite）を Path 型で提供
    - is_live / is_paper / is_dev の簡易判定

- AI（自然言語処理）モジュール (kabusys.ai)
  - news_nlp.score_news
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini, JSON mode）でセンチメントスコアを取得。
    - バッチ処理（1コール最大 20 銘柄）、1銘柄あたり記事上限・文字数トリム（デフォルト: 最大10記事・3000文字）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ・リトライ実装。
    - レスポンスバリデーション（JSON 抽出、"results" 構造、code の正規化・検証、数値チェック）。
    - スコアは ±1.0 にクリップ。取得成功分のみ ai_scores テーブルに置換（DELETE + INSERT）し、部分失敗時に他コードの既存スコアを保護。
    - ルックアヘッドバイアスを避けるため target_date ベースのウィンドウ（前日15:00 JST〜当日08:30 JST 相当）で記事を取得。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で指定。

  - regime_detector.score_regime
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、news_nlp によるマクロセンチメント（重み 30%）を合成し、市場レジーム（bull / neutral / bear）を日次判定。
    - ma200_ratio の計算は target_date 未満のデータのみ使用（ルックアヘッド防止）。
    - マクロニュースは news_nlp.calc_news_window で計算したウィンドウから抽出し、LLM（gpt-4o-mini）で JSON 出力を要求して macro_sentiment を算出。
    - API エラー時はフェイルセーフで macro_sentiment = 0.0 を採用し継続。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時はロールバックを試行し例外を伝播。

- データ管理（kabusys.data）
  - calendar_management
    - market_calendar を使った営業日判定 API を提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にカレンダーがない場合は曜日（平日）ベースのフォールバックを使用。
    - next/prev/get は DB 登録値を優先し、未登録日は曜日フォールバックと一貫して処理。探索上限を設定して無限ループを防止（デフォルト最大 60 日）。
    - calendar_update_job: J-Quants からカレンダー差分取得 → market_calendar へ冪等保存。バックフィル・健全性チェックを実装。

  - pipeline / etl
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。
    - ETLResult により ETL の取得数/保存数/品質問題/エラーを集約。品質問題は (check_name, severity, message) 形式に変換可能。
    - 差分更新、バックフィル、品質チェックの設計方針を実装（jquants_client による取得と保存を想定）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得など。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）・相対 ATR（atr_pct）・20 日平均売買代金（avg_turnover）・出来高比（volume_ratio）を計算。必要行数未満は None。
    - calc_value: raw_financials から直近財務データを取得し PER・ROE を計算（EPS が 0 または欠損のときは None）。
    - 設計: DuckDB 接続を受け取り SQL で計算。外部 API へのアクセスは行わない。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。horizons のバリデーションあり。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。3 件未満で None を返す。
    - rank: 同順位は平均ランクを返す。丸め処理による tie 判定の安定化を実装。
    - factor_summary: count, mean, std, min, max, median を計算（None 値除外）。外部ライブラリに依存せず実装。

- インフラ / 実装細部
  - DuckDB を主な分析 DB として利用する想定で各モジュールが DuckDB の接続オブジェクトを引数に取る設計。
  - OpenAI 呼び出しは各モジュールで独立実装（テスト時に差し替え可能な小さなラッパーを利用）。
  - 多くの箇所でルックアヘッドバイアスを避ける設計（date.today()/datetime.today() を直接参照しない、target_date を明示的に受け取る）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 廃止 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- OpenAI API キーや各種トークンは環境変数経由で管理する設計。Settings は必須トークン未設定時に ValueError を投げるため、シークレット漏洩に注意して環境変数管理を行ってください。
- .env ファイルの読み込みはデフォルトで有効。公開リポジトリで .env を誤ってコミットしないよう注意。

---

注:
- 本 CHANGELOG はコードベース（src/kabusys 以下）から推測して作成した初期リリースの記録です。将来的な変更やリファクタリングに伴い更新してください。