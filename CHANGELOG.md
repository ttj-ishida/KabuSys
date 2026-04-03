Keep a Changelog
=================

すべての変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

フォーマットは Keep a Changelog に準拠します。  

[Unreleased]
------------

（未リリースの変更はここに記載します）

[0.1.0] - 2026-04-03
-------------------

Added
- 初回リリース: パッケージ kabusys を追加。パッケージメタ情報は src/kabusys/__init__.py にあり、__version__="0.1.0"、公開モジュールとして data, strategy, execution, monitoring をエクスポート。
- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出: .git または pyproject.toml を起点に探索して .env/.env.local を自動ロード（パッケージ配布後も動作）。
  - .env 解析: export 形式、シングル/ダブルクォート内のエスケープ、行内コメントの扱いなどに対応する堅牢なパーサーを実装。
  - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 環境変数保護: OS 環境変数を保護するための上書き制御（.env.local は override=True）。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / 監視設定 / システム設定（env, log_level 等）をプロパティとして取得。未設定時のバリデーション（必須キー未設定で ValueError）。
  - KABUSYS_ENV と LOG_LEVEL の許容値チェックを実装。
- AI（自然言語処理）機能（src/kabusys/ai）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（ai_score）を計算して ai_scores テーブルへ書き込む score_news 関数を実装。
    - ニュースウィンドウ（JST 前日15:00〜当日08:30）計算ユーティリティ calc_news_window を提供。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたりの記事数・文字数トリム、JSON レスポンスの厳密なバリデーション、スコアクリップ（±1.0）、部分成功時の安全な DB 書き換え（DELETE → INSERT）を実装。
    - リトライ/バックオフ戦略（429/ネットワーク/タイムアウト/5xx）、およびテスト用に _call_openai_api をモック可能に設計。
    - DuckDB 互換性のため executemany に空リストを渡さないガードを実装（DuckDB 0.10 の制約への対応）。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - 日次で市場レジーム（'bull' / 'neutral' / 'bear'）を判定する score_regime を実装。ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成してレジームスコアを算出。
    - マクロニュース抽出（マクロキーワード群をタイトル検索）と OpenAI 呼び出し、リトライ/バックオフ、API 失敗時のフェイルセーフ（macro_sentiment=0.0）を実装。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）および ROLLBACK ハンドリングを実装。
    - LLM 呼び出しの内部実装は news_nlp と分離（モジュール結合を避ける設計）。
- データプラットフォーム機能（src/kabusys/data）
  - calendar_management モジュール
    - market_calendar を扱う夜間バッチ(calendar_update_job) と営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB 登録データ優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - カレンダー取得のバックフィル・健全性チェック・最大探索日数設定を実装。
  - pipeline / ETL
    - ETLResult データクラスと ETL パイプライン設計（差分取得、保存（idempotent）、品質チェックの流れ）を導入（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）。
    - ETLResult.to_dict が quality_issues を辞書化して返すユーティリティを実装。
    - 内部ユーティリティ（テーブル存在チェック、最終日取得など）を実装。
  - jquants_client と quality モジュールとの連携を意図したインターフェース設計（実装は別モジュール想定）。
- リサーチ機能（src/kabusys/research）
  - factor_research モジュール
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を用いた各種ファクター（モメンタム、MA200乖離、ATR、平均売買代金、PER, ROE 等）を計算。
    - データ不足時の None 処理やログ出力、DuckDB SQL ベースの実装。
  - feature_exploration モジュール
    - calc_forward_returns（任意ホライズンの将来リターン計算）、calc_ic（Spearman ランク相関による IC 計算）、factor_summary（統計サマリ）、rank（同順位平均ランク化）を実装。
    - pandas 等外部ライブラリに依存しない純粋 Python 実装。
  - research パッケージの __init__ で主要関数群を再エクスポート（zscore_normalize は kabusys.data.stats から再エクスポート）。
- ロギング/設計方針
  - ルックアヘッドバイアス防止のため、各モジュールで datetime.today()/date.today() を直接参照しない設計（target_date を引数に取る関数群）。
  - API 呼び出し失敗時はフェイルセーフ戦略（スコアを 0 にフォールバック、該当チャンクをスキップ）を採用し、処理継続性を優先。
  - DuckDB 向けの互換性・注意点（executemany の空リスト不可等）をコード内に明記。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- .env ファイル読み込み時に OS 環境変数を保護する仕組みを導入（.env/.env.local の上書き挙動制御）。
- OpenAI API キー未設定時は明確な ValueError を発生させることで誤動作を防止。

Notes / Implementation details
- OpenAI 呼び出しは gpt-4o-mini の Chat Completions（JSON Mode）を想定。レスポンスの JSON パース失敗や非期待レスポンスに対する防御を行う（余分な前後テキストの復元等）。
- news_nlp と regime_detector はそれぞれ内部で _call_openai_api を持ち、意図的に共有せずモジュール結合を避ける設計。テスト時に patch して差し替え可能。
- DB 書き込みは部分失敗時に既存データを守るため、影響範囲を限定して DELETE → INSERT を行う（例: ai_scores の場合はスコア取得済みコードのみを置換）。
- calendar_update_job は J-Quants クライアント（jquants_client）に依存し、フェイル時には例外を捕捉して 0 を返す設計。

Known issues
- 特になし（初期実装）。実稼働での運用・負荷検証により調整の可能性あり。

Acknowledgements
- 本ドキュメントはソースコード（src/ 以下）から実装意図を抽出して作成しました。実装の詳細は各モジュールの docstring / コメントを参照してください。