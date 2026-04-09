# CHANGELOG

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
コードベースの内容から推測して作成しています。

全般的な注意:
- バージョン番号はパッケージの __version__ (0.1.0) に基づきます。
- 日付はこの生成日を使用しています。

## [Unreleased]

## [0.1.0] - 2026-04-09
初回公開リリース。以下の主要機能と実装を含みます。

### Added
- 環境 / 設定管理
  - .env ファイルおよび環境変数から設定を自動ロードする機能を実装。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。.env.local は .env を上書き。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで自動ロードを無効化可能（テスト用途）。
  - .env パーサは以下に対応:
    - 空行・コメント行（#）の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - 行内コメントの扱い（クォートなしの場合は直前が空白/タブならコメントとみなす）
  - Settings クラスを提供し、必須変数の検証（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）やデフォルト値を管理。
  - KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE などの値チェックと不正値時の例外発生実装。

- ポートフォリオ構築（pure functions）
  - 銘柄選定:
    - select_candidates: score 降順、同点は signal_rank の昇順でタイブレーク。max_positions により上位 N 件を選択。
  - 重み計算:
    - calc_equal_weights: 等金額配分（各銘柄 1/N）。
    - calc_score_weights: スコア加重配分。全てのスコア合計が 0 の場合は等配分にフォールバックし WARNING を出力。
  - リスク調整:
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合、同セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime ('bull'/'neutral'/'bear') に応じた投下資金乗数を提供。未知レジームはフォールバックで 1.0、warn ログ出力。
  - 株数決定 / サイズ調整:
    - calc_position_sizes: allocation_method に応じて発注株数を計算（risk_based / equal / score）。
    - risk_based: 許容リスク率（risk_pct）と損切り率（stop_loss_pct）からベース株数を算出。
    - equal/score: 重みと価格を用いて per-position 上限・aggregate 上限を考慮した株数決定。
    - 単元株（lot_size）単位で丸め、cost_buffer を用いて手数料・スリッページを保守的に見積もり、aggregate cap 超過時はスケールダウンと端数配分のアルゴリズムを実装。

- リサーチ / ファクター計算（DuckDB ベース、外部 API を使わない設計）
  - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離（ma200_dev）を計算。データ不足時は None。
  - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。ウィンドウ内行数チェックあり。
  - calc_value: raw_financials から直近の財務データを取得し PER（EPS が 0/欠損のときは None）と ROE を計算。
  - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを一括取得。ホライズン検証（正の整数かつ <= 252）。
  - calc_ic / rank: スピアマンのランク相関（IC）を算出するユーティリティ。ties の平均ランク処理を実装。
  - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

- AI（LLM）連携機能（OpenAI を利用）
  - ニュースセンチメント（news_nlp）
    - score_news: raw_news と news_symbols を集約し、銘柄ごとに gpt-4o-mini（JSON Mode）でセンチメント評価を実行。
    - バッチ処理（デフォルト最大 20 銘柄/リクエスト）、記事数・文字数のトリム制御（最大記事数・最大文字数）。
    - リトライ/バックオフ: 429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフでリトライ（最大回数設定あり）。
    - レスポンス検証: JSON パース、results 配列、各要素の code/score 検証、スコアを ±1.0 にクリップ。
    - DuckDB への書き込みは冪等操作（DELETE → INSERT）で、部分失敗時に既存スコアを保護する実装。
    - API キーは引数または OPENAI_API_KEY 環境変数から取得。未設定時は ValueError を送出。
  - レジーム判定（regime_detector）
    - score_regime: ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを合成してレジーム判定（'bull' / 'neutral' / 'bear'）を行い market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出はキーワードフィルタ（複数キーワード）によるタイトル収集。記事がない場合は macro_sentiment=0 として継続（フェイルセーフ）。
    - 合成ロジック: ma200 の寄与を重め（70%）、マクロセンチメントを 30% としスコアを clip(-1,1)。閾値でラベル付け。
    - API 呼び出しやパース失敗は安全側のフォールバック（ログ出力）で処理。

- モニタリング永続化（SQLite）
  - init_monitoring_db: 監視ログ用に 5 テーブルと必要なインデックスを冪等に作成するユーティリティを実装。
    - 作成されるテーブル例: system_status, trade_logs, positions, risk_logs（計 5 テーブル + 各種インデックス）。
    - テーブルは監視データ・トレードログ・ポジション等の永続化を目的とする読み書き専用レイヤー。

- パッケージ初期化／エクスポート
  - kabusys パッケージの __version__ を 0.1.0 に設定。
  - portfolio / research / ai モジュール API を __all__ で整理してエクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Internal / Notes
- 多くの関数は DuckDB 接続を受け取り、外部 API 呼び出しを避ける設計（ルックアヘッドバイアスの防止）。
- OpenAI 呼び出しはテスト容易性のため _call_openai_api をラップしており、テストでモック差替え可能。
- TODO 注記: 単元株 lot_size の銘柄別化、価格欠損時のフォールバックロジックなど将来的な拡張ポイントあり。
- ロギングを多用して挙動のトレーサビリティを確保。警告・デバッグ出力が各所に実装されている。

---

今後の変更履歴には、バグ修正、性能改善、外部依存（OpenAI SDK 変更等）への対応、新機能（PBR/配当利回りの実装、銘柄別 lot_size など）を記載してください。