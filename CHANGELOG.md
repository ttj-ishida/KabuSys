# Changelog

すべての注目すべき変更をこのファイルで管理します。This project adheres to "Keep a Changelog" とセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-29

### 追加
- 初期リリース: kabusys パッケージのコア機能を実装。
  - パッケージメタ情報:
    - バージョン: 0.1.0
    - パブリッシュ対象モジュール: data, research, ai, config 等を公開。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
  - .env パーサ実装:
    - export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、
    - インラインコメントの扱い（クォート有無で挙動を区別）等を正しく処理。
  - 読み込み優先順: OS 環境変数 > .env.local > .env（.env.local は上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - Settings クラスを提供し、各種必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）やデフォルト値（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV）を取得可能。環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL）を実装。

- データ基盤（kabusys.data）
  - calendar_management:
    - market_calendar を基にした営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録がない場合の曜日ベースフォールバック（週末を非営業日とする）をサポート。
    - calendar_update_job を実装（J-Quants API から差分取得 → 冪等保存 / バックフィル / 健全性チェック）。
    - DuckDB との互換性と日付変換ユーティリティを提供。
  - pipeline / etl:
    - ETLResult データクラス（ETL 実行結果の集約）を実装・公開。
    - ETL モジュールのユーティリティ（差分取得、最大日付取得等）を実装。
    - jquants_client と quality モジュール連携を想定した設計（差分取得・保存・品質チェックのワークフロー）。
    - DuckDB に対する実装上の注意（executemany に空リストを渡さない等）を反映。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS が無効な場合は None）。
    - DuckDB 上で SQL とウィンドウ関数を用いて効率的に計算。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を使用）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank: 同順位は平均ランクを採るランク付け実装（丸めで ties 対応）。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算。
  - research パッケージの __init__ で主要 API を再エクスポート。

- AI / NLP（kabusys.ai）
  - news_nlp:
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols を集約し、銘柄ごとに LLM（gpt-4o-mini）でセンチメントを計算して ai_scores テーブルへ書き込む。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST に対応（UTC 変換済み）。
    - バッチング（最大 20 銘柄/回）、1 銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）によるプロンプト制限。
    - レスポンスの厳格なバリデーションとスコアの ±1.0 クリップ。
    - リトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実装。失敗時は対象チャンクをスキップして処理継続するフェイルセーフ設計。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - regime_detector:
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを合成して日次の market_regime レコードを冪等に書き込む。
    - レジーム合成ロジック（MA 重み 70%、マクロ重み 30%、スコアのクリップ、閾値に基づくラベリング bull/neutral/bear）。
    - マクロニュース抽出はキーワードベース（デフォルトリストあり）、記事がない場合は LLM 呼び出しをスキップして macro_sentiment=0.0。
    - API 呼び出しや JSON パース失敗時は安全に 0.0 にフォールバックするフェイルセーフ。
    - OpenAI クライアントは OpenAI SDK を利用し、retry などの振る舞いを実装。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### セキュリティ
- OpenAI API を利用する関数（score_news, score_regime）は API キーが未設定の場合に ValueError を送出して明示的なエラー扱いにすることで誤実行を防止。
- .env 読み込み時に OS 環境変数を保護する機構（protected set）を実装し、.env による意図しない上書きを防止。

### 注意事項 / 実装上の設計判断（ドキュメント的備考）
- ルックアヘッドバイアス防止:
  - AI / ニュース / レジーム算出の各モジュールは内部で datetime.today() / date.today() を参照せず、呼び出し側が target_date を明示的に渡す設計。
  - DB クエリは target_date 未満や半開区間などで将来データ参照を避けるよう工夫されている。
- DuckDB 互換性のための注意:
  - executemany に空リストを渡してはいけない制約に対応（空チェックを行う）。
  - 日付データの変換ユーティリティを提供。
- 外部依存の最小化:
  - 研究系モジュールは pandas 等の外部ライブラリに依存しない標準ライブラリ + DuckDB のみで実装。
- テストしやすさ:
  - OpenAI 呼び出し点（_call_openai_api）を patch 可能にするなど、単体テストやモック利用を容易にしている。

---

今後の予定（例）
- strategy / execution / monitoring のコア実装（取引ロジック、発注モジュール、モニタリング）を段階的に追加。
- jquants_client, quality モジュールの実装・安定化と ETL の運用検証。
- ユニットテスト、統合テスト、CI ワークフローの整備。

もし CHANGELOG に加えたい具体的な変更点（リリース日や貢献者、マイナー修正など）があれば教えてください。