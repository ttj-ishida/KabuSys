CHANGELOG
=========
すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。  
フォーマットについて: https://keepachangelog.com/ja/

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-01
-------------------

Added
- 初回公開リリースを作成。
- パッケージ基盤
  - kabusys パッケージの公開（__version__ = 0.1.0）。
  - パッケージのトップレベルで data, strategy, execution, monitoring をエクスポート。
- 設定管理 (kabusys.config)
  - .env / .env.local からの自動環境変数読み込み機能を導入（プロジェクトルート判定は .git または pyproject.toml を参照）。
  - .env パーサの実装：export 構文対応、シングル/ダブルクォートとバックスラッシュエスケープ対応、インラインコメント処理（未クォート値は '#' 前が空白の場合コメントと判定）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境変数保護（OS 環境変数を上書きしない仕組み）と override オプション。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境（development/paper_trading/live）/ログレベル等のプロパティを取得。未設定時の明示的エラー（必須キーは ValueError）や値検証を実装。
- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄毎にニューステキストを作成し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ計算（JST 前日15:00〜当日08:30 を UTC に変換）を提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄/回）、記事数・文字数トリム、JSON 応答の堅牢なバリデーション、スコアの ±1.0 クリップ。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフでのリトライ。API 失敗やパース失敗はフェイルセーフとして該当チャンクをスキップし、全体処理を継続。
    - スコアを ai_scores テーブルへ冪等的に（DELETE → INSERT）書き込み。部分失敗時に既存データを保護する実装。
    - テストしやすさのため _call_openai_api を差し替え可能（unittest.mock.patch 想定）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し日次で市場レジーム（bull/neutral/bear）を算出。
    - prices_daily / raw_news を参照し、ma200_ratio とマクロセンチメントを算出。OpenAI 呼び出しに対してリトライ・フェイルセーフを実装（失敗時 macro_sentiment=0.0）。
    - 結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - LLM 呼び出しは別モジュールと共有しない独立実装でモジュール結合を抑制。
- Data モジュール (kabusys.data)
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルに基づく営業日判定 API を提供：is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値を優先し、未登録日は曜日ベース（週末除外）でフォールバック。最大探索日数を設定して無限ループ防止。
    - JPX カレンダーの夜間バッチ更新ジョブ calendar_update_job（J-Quants から差分取得 → 保存）を実装。バックフィルと健全性チェックを実施。
  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult データクラスを提供（取得件数・保存件数・品質チェック結果・エラー情報等を保持）。to_dict により品質問題をシリアライズ可能。
    - 差分更新・バックフィル・品質チェックの設計方針実装（概要）。jquants_client と quality モジュールを組み合わせた処理想定。
    - パイプラインユーティリティを公開（ETLResult を etl モジュールで再エクスポート）。
- Research モジュール (kabusys.research)
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。データ不足時の None ハンドリング。
    - ボラティリティ/流動性: 20 日 ATR（true range の厳密処理）、相対 ATR、20 日平均売買代金、出来高比率。
    - バリュー: raw_financials から最新財務を取得して PER（EPS が 0 または欠損なら None）と ROE を計算。
    - SQL + DuckDB ウィンドウ関数中心の実装で、外部 API にはアクセスしない設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン calc_forward_returns（任意ホライズン、デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算 calc_ic（Spearman ランク相関）。少数レコードや分散ゼロの扱いに配慮。
    - ランク化ユーティリティ rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）。
- その他
  - パッケージのテスト容易性を考慮したポイントを多数実装（OpenAI 呼び出し差し替え可能等）。
  - DuckDB を主要な内部 DB として想定した実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 実装上の注意
- ルックアヘッドバイアス防止のため、各種処理は内部で datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る）。
- OpenAI（gpt-4o-mini）を用いる箇所ではレスポンスパース失敗や API 障害時にフェイルセーフで継続する実装になっているため、運用時は API を安定的に供給するか監視ログを確認してください。
- .env の自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布後の挙動は環境により変わる可能性があります。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を指定してください。
- 一部の関数（例: pipeline._get_max_date の実装断片）はソースの一部が継続実装を想定しています。詳細は該当ソースを参照してください。

Acknowledgements / Dependencies
- DuckDB、OpenAI Python SDK を利用する想定の実装。その他標準ライブラリを使用。

---