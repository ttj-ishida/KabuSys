CHANGELOG
=========

すべての重要な変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
-------------

- なし

[0.1.0] - 2026-04-04
--------------------

初回公開リリース。日本株自動売買プラットフォーム「KabuSys」のコア機能を含むパッケージを初版として公開します。

Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0 に設定。
  - パッケージの公開 API: data, strategy, execution, monitoring を __all__ で定義。

- 環境変数/設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートの検出は __file__ を基準に .git または pyproject.toml を探索（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントなどに対応。
    - 読み込み時に OS 環境変数を保護する protected キーセットを採用（.env.local は上書き可能だが OS 環境変数は保護）。
  - Settings クラスを提供し、明示的なプロパティ経由で設定値を取得可能（必須キーは _require による ValueError）。
    - J-Quants / kabuステーション / LINE / DB パス / 監視設定 / システム env/log_level のプロパティを実装。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値のみ受け付ける）。
    - デフォルトの DB パス（duckdb: data/kabusys.duckdb, sqlite: data/monitoring.db）や監視ファイルパスを設定。

- AI (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news, news_symbols テーブルから記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - JST 基準のニュースウィンドウ（前日 15:00 ～ 当日 08:30 JST）を calc_news_window で計算。
    - 1 銘柄あたり最大記事数／文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄／回）とエクスポネンシャルバックオフ／リトライ（429・ネットワーク断・タイムアウト・5xx をリトライ対象）。
    - レスポンスの厳密なバリデーション（JSON 抽出・results リスト・code/score 確認・数値変換・±1.0 クリップ）。
    - スコア書き込みは部分失敗時に既存データを保護するため対象コードのみ DELETE → INSERT の冪等更新。
    - テスト容易性のため OpenAI 呼び出し部分は _call_openai_api を差し替え可能に実装。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - LLM モデルは gpt-4o-mini、出力は厳密な JSON（{"macro_sentiment": ...}）を期待。
    - マクロニュースの抽出はマクロキーワードリストに基づき raw_news のタイトルをフィルタ（最大 _MAX_MACRO_ARTICLES）。
    - API エラー時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）で market_regime テーブルに保存。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計。prices_daily クエリは target_date 未満の排他条件あり。
    - リトライ・バックオフを実装し、OpenAI API の 5xx/ネットワークエラー等に対処。

- データ (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得→冪等保存。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを提供。
    - market_calendar が未取得のケースでは曜日ベース（土日非営業）でフォールバックする一貫した挙動を採用。
    - 最大探索範囲や健全性チェック（未来日付の異常検出）、バックフィル日数の考慮を実装。
  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分取得、保存（jquants_client の save_* を利用した冪等保存）、品質チェック（quality モジュール連携）を想定した設計。
    - デフォルトのバックフィルやカレンダー先読み等、実運用を意識した動作。
    - ETLResult.to_dict() により品質問題を辞書化して監査ログ等で扱えるように実装。

- リサーチ (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、流動性指標）、Value（PER、ROE）を DuckDB の prices_daily / raw_financials を用いて計算する関数を実装。
    - データ不足時の扱い（該当ファクターを None）やログ出力を実装。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン calc_forward_returns（ホライズン指定可、入力検証あり）、IC（Spearman ランク相関）calc_ic、rank、factor_summary 等の統計補助関数を実装。
    - pandas 等に依存せず、標準ライブラリ + DuckDB で計算。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- 環境変数の取り扱いに注意:
  - 必須トークン（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）は Settings のプロパティで取得し、未設定時は ValueError を発生させることで明示的な設定を促す。
  - .env 自動読み込み時に OS 環境変数を上書きしない保護機構（protected keys）を導入。
  - OpenAI API キーは引数で注入可能（テスト容易性）だが、未設定時は環境変数 OPENAI_API_KEY の設定を要求。

Notes / Design decisions
- ルックアヘッドバイアス回避のため、日付ロジックは明示的に target_date を受け取り、datetime.today()/date.today() を直接使わない設計を優先。
- DuckDB を一次的な分析 DB と想定し、executemany の空リストバインドや型差異に配慮した実装（例: executemany 前に空チェック）。
- OpenAI 呼び出しは JSON Mode を活用し厳密なレスポンスを期待する一方で、パース失敗や API 障害時は安全側のフォールバック（スコア 0.0 や処理スキップ）を行う。
- テスト容易性のため、OpenAI 呼び出し箇所（_call_openai_api 等）をモック差し替え可能に設計。

Known issues / Limitations
- JSON Mode でも出力に余計なテキストが混入する可能性があるため、追加の JSON 抽出ロジックを実装しているが、全ケースを保証するものではありません。
- ai_scores / market_regime など書き込み先テーブルのスキーマ依存があるため、事前に期待されるテーブル定義を準備する必要があります。
- 現時点では PBR や配当利回りなど一部のバリューファクターは未実装。

---

開発者向け: 変更やバグ修正、機能追加を行う際は、Keep a Changelog の原則に従い、Unreleased セクションを更新してください。