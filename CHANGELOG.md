# Changelog

すべての重要な変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。  
バージョン番号はパッケージの src/kabusys/__init__.py に基づきます。

なお、記載内容はリポジトリ内のコード・ドキュメントから推測してまとめたものです。

全般ルール:
- すべての日付・時刻はソースコメントに従い timezone 混入を避ける実装方針があるため、主に date / datetime（naive）で扱われます。
- DuckDB を主要なローカルデータストアとして利用します。
- OpenAI（gpt-4o-mini）を用いた NLP 処理には冗長なリトライ / フォールバック / レスポンス検証が組み込まれています。

Unreleased
----------
- （なし）

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージトップ (src/kabusys/__init__.py) における公開 API の定義。__version__ = "0.1.0"、__all__ に data, strategy, execution, monitoring を設定。

- 環境設定/ローダー (src/kabusys/config.py)
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントの取り扱いなどに対応。
  - 読み込み時の上書き挙動（override）・OS 環境変数保護（protected set）をサポート。
  - Settings クラスを提供し、必須環境変数取得（_require）や検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）、デフォルト値（KABUSYS_API_BASE_URL など）、パスの expanduser 処理（duckdb/sqlite のデフォルトパス）を実装。
  - Slack / kabu API / J-Quants 用の設定プロパティを定義（例: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD, JQUANTS_REFRESH_TOKEN）。

- AI モジュール
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約し、銘柄ごとにニューステキストを結合して OpenAI（gpt-4o-mini）へバッチ送信し、ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を calc_news_window として公開。
    - バッチ処理（デフォルト 20 銘柄）、1 銘柄あたりの最大記事数/最大文字数制限、JSON Mode のレスポンス検証、レスポンスからのスコア抽出と ±1.0 のクリップ。
    - API 呼び出し時のリトライ（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）と、失敗時はスキップしてフェイルセーフに継続する設計。
    - DuckDB 書き込みは部分失敗を考慮して、取得済みコードのみ DELETE → INSERT する冪等的な置換ロジックを採用。
    - テスト容易性のため _call_openai_api をローカルに定義してモック差し替え可能。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して当日ベースの市場レジーム（bull / neutral / bear）を判定し、market_regime テーブルへ冪等書き込みする処理を実装。
    - マクロニュース抽出用のキーワードリスト（日本・米国／グローバル）を定義。最大記事数制限を設定。
    - OpenAI 呼び出しは独立実装で、API エラーやパース失敗時には macro_sentiment = 0.0 のフェイルセーフを適用。
    - 再試行戦略（最大リトライ・指数バックオフ）と 5xx 判定の取り扱い（APIError の status_code を安全に扱う実装）を導入。
    - ルックアヘッドバイアス防止のため target_date 未満のデータのみを使用。date.today() 等を参照しない設計方針を明記。

- Research（因子 / 特徴量分析） (src/kabusys/research/*)
  - ファクター計算 (factor_research.py)
    - Momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を DuckDB のウィンドウ関数で計算。
    - Volatility / Liquidity: 20 日 ATR（atr_20, atr_pct）、20 日平均売買代金、出来高比率を実装。
    - Value: raw_financials から最新の財務データを取得して PER / ROE を計算（EPS が 0/欠損時は None）。
    - 欠損やデータ不足時の None ハンドリング、DuckDB の SQL ベースで高速に計算する設計。
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）：任意のホライズン（デフォルト [1,5,21]）に対応。horizons の検証（正の整数かつ <=252）。
    - IC（Information Coefficient）計算（calc_ic）：Spearman ρ をランクを用いて算出。充分なサンプル数がない場合は None を返す。
    - ランク変換ユーティリティ（rank）：同順位は平均ランク、丸め誤差対策として round(v, 12) を使用。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を計算。
  - zscore_normalize は data.stats から再エクスポート。

- Data（ETL / カレンダー / pipeline） (src/kabusys/data/*)
  - カレンダー管理 (calendar_management.py)
    - market_calendar テーブルを参照して営業日判定・次/前営業日の探索・期間内営業日取得を行うユーティリティを実装。
    - DB にデータがない場合の曜日ベースフォールバック（週末を非営業日扱い）を採用し、DB 登録値がある場合は優先。
    - calendar_update_job を実装し、J-Quants API から差分取得して market_calendar テーブルを冪等で更新（バックフィル期間・最大探索日数・健全性チェックを含む）。
  - ETL パイプライン (pipeline.py / etl.py)
    - ETLResult データクラスを公開（ETL の集計結果・品質問題・エラーメッセージを格納）。
    - 差分取得ロジック、最終取得日の取得ユーティリティ、バックフィルのデフォルト設定、品質チェックフロー（quality モジュール連携）を実装。
    - jquants_client 経由の idempotent 保存処理を想定。
    - エラー／品質問題を集約して呼び出し元に返す設計（Fail-Fast ではなく問題収集に注力）。

- テスト・開発支援
  - OpenAI 呼び出し部分に対して簡単にモック差し替えできるよう _call_openai_api を各モジュールでローカルに定義（unit test 用の patch を想定）。
  - ロギング（logger）を各モジュールに導入し、重要なイベント・フォールバック・例外を記録。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 実装上の重要点（ドキュメント的補足）
- Look-ahead バイアス対策: AI スコア・レジーム判定・ETL 等で datetime.today() / date.today() を直接参照しないことを明確に設計に反映。target_date を明示的に受け取り、DB クエリは排他条件（< target_date など）を用いる。
- DB 書き込みは可能な限り冪等性を確保（DELETE→INSERT、ON CONFLICT / executemany の扱いに注意）。
- OpenAI のレスポンスは厳密な JSON を要求するが、実運用では前後のノイズを復元する耐性（最外の {} を抽出して JSON パースを試みる）を実装。
- 各所で入力検証（env 値、horizons の範囲、JSON の形式チェック等）とフォールバックが行われるため、運用時の堅牢性が高い実装となっている。

Security
- API キーは引数で注入可能（テスト容易性）かつ環境変数から取得。必須キーが未設定の場合は ValueError を送出して明示的に失敗する設計。
- 環境変数の上書きロジックは OS 環境変数を protected として保持する仕組みを持つ。

今後の改善候補（推奨）
- unit tests / integration tests の整備（特に OpenAI 呼び出しのモックを用いた回帰テスト）
- OpenAI のレスポンススキーマ変更やモデル切替に備えた抽象化層の強化
- DuckDB のバージョン依存の挙動（リストバインド等）に対する互換性テストの追加
- ETL の部分失敗時におけるリカバリ / 再実行ポリシーの明文化

---- 

（以上）