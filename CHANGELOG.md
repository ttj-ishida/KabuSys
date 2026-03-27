# Changelog

すべての注記は Keep a Changelog のフォーマットに従います。  

注: この CHANGELOG は提供されたコードベースの実装から推測して作成しています。実際のコミット履歴ではなく、実装上の「追加」「変更」「修正」とみなせる点をまとめたものです。

## [Unreleased]

- （現在のリポジトリに対する未リリースの変更はありません）

## [0.1.0] - 2026-03-27

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報: __version__ = "0.1.0"、主要サブパッケージを __all__ に公開（data, strategy, execution, monitoring）。
- 環境設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサー実装: export KEY=val、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 既存 OS 環境変数は保護（protected）し、override オプションで .env.local による上書きが可能。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス / 実行環境・ログレベル等のプロパティを環境変数から取得（未設定時にエラーを投げる必須取得メソッドも含む）。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値のバリデーション）を実装。

- データ処理（kabusys.data）
  - ETL インターフェースの公開（ETLResult を pipeline モジュールから再エクスポート）。
  - pipeline モジュール: 差分取得・保存・品質チェックに関する ETL 用ユーティリティを実装。ETLResult dataclass により取得数・保存数・品質問題・エラー概要を集約。
  - calendar_management モジュール: JPX カレンダーの夜間更新ジョブ (calendar_update_job)、営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - market_calendar テーブルがない場合は曜日ベースでフォールバック。
    - 最大探索日数やバックフィル、健全性チェック等の安全装置を実装（_MAX_SEARCH_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS 等）。
    - J-Quants クライアントとの差分フェッチおよび idempotent な保存フローを想定。

- 研究・ファクター（kabusys.research）
  - ファクター計算モジュールを実装（factor_research.py）。
    - モメンタム: mom_1m / mom_3m / mom_6m、200日 MA 乖離（ma200_dev）を計算する calc_momentum。
    - ボラティリティ/流動性: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算する calc_volatility。
    - バリュー: PER、ROE を raw_financials と prices_daily から算出する calc_value。
    - DuckDB 上で SQL＋ウィンドウ関数を駆使して効率的に集計。
  - 特徴量探索（feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）のリターンを一度のクエリで取得。
    - IC（Information Coefficient）計算（calc_ic）: Spearman のランク相関（ランクは平均ランク処理）を計算、データ不足時は None を返す。
    - ランク関数（rank）: 同順位は平均ランクにする実装（浮動小数丸めで ties 対応）。
    - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median を標準ライブラリのみで計算。
  - zscore_normalize を data.stats から再エクスポートする仕組み（__init__）。

- AI / 自然言語処理機能（kabusys.ai）
  - ニュース NLP スコアリング（news_nlp.py）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチで送信して銘柄単位のセンチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を対象（UTC への変換を実装）で calc_news_window を提供。
    - バッチ処理: 最大 _BATCH_SIZE（20銘柄）単位で API 呼び出し、1銘柄あたり最大記事数・最大文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ実装。その他エラーはスキップして継続（フェイルセーフ）。
    - API レスポンスのバリデーション（JSON の頑健な復元、results 配列チェック、コード整合性チェック、数値チェック、スコアのクリップ）を実装。
    - DuckDB の executemany が空リストを受け付けない制約への対応（params が空でないことを確認して実行）。
  - 市場レジーム判定（regime_detector.py）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定し、market_regime テーブルへ冪等書き込み。
    - MA 計算は target_date 未満データのみを使用してルックアヘッドを防止。
    - マクロ記事抽出は news_nlp の calc_news_window を利用、OpenAI を用いたセンチメント評価（gpt-4o-mini）を実行。
    - API 呼び出しは冗長なリトライ処理を実装し、全リトライ失敗時は macro_sentiment=0.0 にフォールバック（例外を投げず継続）。
    - トランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に DB 書き込み。

Changed
- 設計方針・安全性に関する共通方針をコード注釈として導入
  - ルックアヘッドバイアス回避のため datetime.today()/date.today() を直接参照しない実装（target_date を引数で明示）。
  - DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT の想定）。
  - API フェイルセーフ: 外部 API 失敗時は例外を極力伝播させず、局所でフォールバックして処理継続。

Fixed
- DuckDB に関する運用上の注意対応
  - executemany に空リストを渡すとエラーになる点を考慮し、空チェックを実装して回避。
- .env 読み込みエラーを警告に落とすことで起動中断を防止（warnings.warn を使用）。

Security
- 環境変数の上書きガード:
  - .env 読み込み時に既存 OS 環境変数を protected として保護し、意図せぬ上書きを防止。
- 必須 API キーのチェックを行い、未設定時には明確な ValueError を送出（OpenAI 等のキー漏れを明示）。

Removed
- なし

Deprecated
- なし

Notes / Implementation details
- OpenAI クライアント呼び出し箇所はテスト容易性を考慮し内部関数でラップしてあり、unittest.mock.patch による差し替えがしやすい実装になっている。
- JSON Mode（response_format={"type": "json_object"}）を利用する想定で、応答パースの堅牢化ロジックを実装している（前後の余計なテキストをトリムして {} を抽出する等）。
- 各モジュールは外部に副作用を与えないこと（DB スキーマや外部 API 呼び出しの注入）を意識した設計になっている。

Contributors
- 実装コードから推測して作成。実際のコントリビュータはリポジトリのコミット履歴を参照してください。