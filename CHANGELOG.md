# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベース（バージョン 0.1.0）から推測して作成した初期リリース向けの変更履歴です。

注: 日付はこの生成日（2026-04-01）を使用しています。実際のリリース時には適宜更新してください。

## [Unreleased]

## [0.1.0] - 2026-04-01
初期リリース。以下の主要機能とモジュールを実装／公開しました。

### 追加 (Added)
- パッケージエントリポイント
  - kabusys パッケージの基本定義（src/kabusys/__init__.py）。公開サブモジュール: data, strategy, execution, monitoring。
  - バージョン文字列 __version__ = "0.1.0" を設定。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local または既存の OS 環境変数から設定を自動読み込みする仕組みを実装（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準に __file__ から探索）を実装。
  - .env パーサーを実装:
    - export KEY=val 形式やシングル／ダブルクォート、バックスラッシュエスケープ、行内コメント処理に対応。
  - 環境変数上書きポリシー（.env と .env.local の読み込み順、OS 環境変数の保護）を実装。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DBパス / 監視閾値 / システム設定等をプロパティ経由で取得。
  - KABUSYS_ENV と LOG_LEVEL のバリデーション（許可値チェック）を実装。
  - 必須値未設定時は _require() が ValueError を送出し明示的に知らせる設計。

- AI 関連モジュール (src/kabusys/ai/)
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとにニューステキストをまとめ、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを評価。
    - バッチサイズ、記事数上限、文字数トリム、JSON Mode を用いた堅牢なレスポンス処理などを実装。
    - リトライ（429、ネットワークエラー、タイムアウト、5xx）を指数バックオフで行う。
    - レスポンス検証（JSONパース、results リスト、code の整合性、数値変換、スコアのクリップ）を実装。
    - 結果を ai_scores テーブルへ冪等的に保存（DELETE → INSERT、部分失敗に備えたコード絞込）。
    - calc_news_window ユーティリティを提供（JST の前日 15:00 ～ 当日 08:30 に対応する UTC 範囲を返す）。
    - API キー注入（api_key 引数または環境変数 OPENAI_API_KEY）。

  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定。
    - MA 計算、マクロキーワードによる記事抽出、LLM 呼び出し（独自の _call_openai_api）および再試行ロジック、フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）で market_regime テーブルを更新。
    - OpenAI キーの注入をサポート（api_key 引数 or OPENAI_API_KEY）。

  - ai パッケージの公開（src/kabusys/ai/__init__.py）で score_news を再エクスポート。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - factor_research.py:
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離。
    - Volatility: 20 日 ATR（true range を正しく扱う）、相対 ATR、20 日平均売買代金、出来高比率。
    - Value: raw_financials から EPS/ROE を取得して PER/ROE を計算。
    - DuckDB を用いた SQL ベースの集計で、結果は (date, code) をキーとする dict のリストで返す設計。
  - feature_exploration.py:
    - 将来リターン計算（任意ホライズン、入力バリデーション、効率的なリード使用）。
    - IC（Spearman の ρ）計算、ランク変換ユーティリティ（同順位は平均ランク）、ファクター統計サマリー（count/mean/std/min/max/median）。
  - research パッケージ公開（src/kabusys/research/__init__.py）で主要関数群をエクスポート。
  - 研究系関数は外部依存（pandas 等）を使わず標準ライブラリ + DuckDB のみで実装。

- データ基盤 (src/kabusys/data/)
  - calendar_management.py:
    - JPX カレンダー管理（market_calendar テーブル参照）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。DB 登録値があれば優先し、未登録は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job による J-Quants からの差分取得（バックフィル、健全性チェック、jquants_client の fetch/save を使用）。
    - 最大探索日数やバックフィル／先読み日数の定数を導入して過度な探索や未来日付異常を防止。

  - pipeline.py / etl.py:
    - ETLResult データクラスを実装し、ETL 処理の取得数／保存数／品質問題／エラー情報をまとめて返却可能に。
    - 差分取得・バックフィルの方針、保存は冪等（jquants_client の save_*）、品質チェックモジュールとの連携設計。
    - デフォルトの最小データ開始日やバックフィル日数等の定数を定義。
    - data/etl.py は ETLResult を再エクスポート。

- その他
  - data パッケージの __init__.py（空のプレースホルダファイル）を追加。
  - ロギング文言を各モジュールに追加して処理状況や警告を記録。

### 変更 (Changed)
- なし（初期リリース）。

### 修正 (Fixed)
- なし（初期リリース）。

### 既知の問題 / 注意点 (Known issues / Notes)
- pipeline._get_max_date の末尾がファイル断片で途切れている模様（ソースの最後に "return date.fro" といった不完全な行が見られます）。この部分は未完成または編集の途中で切れている可能性が高く、ビルド／実行時に構文エラーになる可能性があります。リリース前に該当関数の完全な実装（正しい日付返却ロジック）を確認してください。
- src/kabusys/data/__init__.py は現在空です。将来のサブモジュール公開や依存解決のために内容を追加することが想定されます。
- OpenAI API 呼び出しは外部通信に依存するため、API キーが必要です（api_key 引数または環境変数 OPENAI_API_KEY）。API 失敗時は多くの部分でフォールバック（0.0 やスキップ）する実装になっており、これによりフェイルセーフを確保していますが、精度低下の原因になります。
- .env パーサーは多くのケースに対応していますが、特殊な .env フォーマットや非常に複雑なエスケープケースは想定外の動作となる可能性があります。必要に応じてテストを行ってください。
- DuckDB に対する executemany の空リストバインド制約（DuckDB 0.10 の制約）に配慮した実装になっています。空リストの扱いには注意してください。
- すべての「日付」処理はルックアヘッドバイアスを避ける設計（datetime.today／date.today を直接参照しない）になっている点に留意してください。テスト時は target_date を明示的に渡すことが前提です。

### セキュリティ (Security)
- 特になし（初期リリース）。ただし環境変数や API キー取り扱いのベストプラクティスを遵守してください。

---

この CHANGELOG はコードの内容から推測して作成しています。実際のリリースノートとして使用する場合は、実装担当者による確認・修正を行ってください。