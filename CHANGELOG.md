CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは「Keep a Changelog」に準拠します。  

Unreleased
----------

- なし

[0.1.0] - 2026-03-31
--------------------

Added
- 初回リリース: kabusys パッケージ v0.1.0 を公開
  - パッケージメタ情報:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
    - 公開モジュール: data, research, ai, execution, monitoring, strategy（__all__ 経由）
- 環境設定/読み込み機能 (src/kabusys/config.py)
  - プロジェクトルート検出: .git または pyproject.toml を起点に自動検出（CWD 非依存）
  - .env ファイル自動読み込み:
    - 優先順位: OS 環境変数 > .env.local > .env
    - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - .env のパース機能を独自実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理等に対応）
    - 既存 OS 環境変数は保護（protected set）して上書きを回避
  - Settings クラス:
    - J-Quants / kabuステーション / Slack / DB / 監視 / ログ等のプロパティを提供
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の値検証を実装
    - 標準的なパス（duckdb/sqlite/pid）や閾値（CPU/Memory/Disk）をデフォルト値で提供
    - 必須変数未設定時は明示的に ValueError を送出
- AI モジュール (src/kabusys/ai)
  - news_nlp (src/kabusys/ai/news_nlp.py)
    - raw_news + news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）で銘柄別センチメントを算出
    - バッチ処理（最大20銘柄／チャンク）、記事トリム（最大記事数・文字数制限）を実装
    - OpenAI 呼び出しは JSON モードを使用し、応答のバリデーション（results 配列、各要素 code/score、数値チェック）を行う
    - リトライ方針: 429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフで再試行
    - 書き込みはトランザクションで idempotent に行い、部分失敗時に既存データを保護（DELETE → INSERT、executemany の空リスト対策あり）
    - API キー未設定時は ValueError を送出
  - regime_detector (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動ETF）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定
    - マクロキーワードで raw_news をフィルタし、OpenAI にて macro_sentiment を取得（記事がない場合は LLM 呼び出しをスキップ）
    - API 呼び出し/パース失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）
    - レジーム結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）
    - ルックアヘッドバイアス対策: date より前（排他）のデータのみ利用、内部で datetime.today() を参照しない設計
- Research モジュール (src/kabusys/research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離の算出（データ不足時は None）
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比の算出
    - calc_value: raw_financials を参照して PER / ROE を計算（EPS が不適切な場合は None）
    - SQL とウィンドウ関数を活用して DuckDB にて効率的に計算
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン（LEAD を利用）をまとめて取得（horizons の検証あり）
    - calc_ic: 因子値と将来リターンの Spearman ランク相関（IC）を計算（有効レコード3件未満で None）
    - rank: 同順位は平均ランクで処理（丸めで ties 判定漏れを防止）
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出
  - kabusys.data.stats からの zscore_normalize を再エクスポート（research パッケージ __init__）
- Data プラットフォーム関連 (src/kabusys/data)
  - calendar_management:
    - JPX カレンダーの管理／夜間バッチ更新処理（calendar_update_job）を実装
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供
    - DB にデータがない場合は曜日ベースのフォールバック（週末を非営業日）を行う設計
    - lookahead / backfill / sanity checks を実装し API 取得の安全性を確保
  - pipeline / etl:
    - ETLResult データクラスを導入（取得件数・保存件数・品質問題・エラーの集約）
    - ETL の差分更新・バックフィル方針・品質チェック設計を反映する骨組みを実装
    - jquants_client（外部モジュール想定）を使った取得／保存フローへのフックを準備
  - etl.py: pipeline.ETLResult を公開インターフェースとして再エクスポート
- 低レベルな動作・運用改善
  - DuckDB の executemany による空リストバインド制約を考慮した実装（空の場合は実行をスキップ）
  - OpenAI クライアント呼び出しを内部関数化してテスト時にモック差し替え可能に設計
  - ロギングと警告の充実（データ不足や API エラー時に明示的ログを出力）
  - ルックアヘッドバイアス防止のため日付参照方法を統一（datetime.today() を内部で参照しない）

Changed
- 初版のため該当なし

Fixed
- 初版のため該当なし

Security
- API キー取り扱い:
  - OpenAI API キーは関数引数で注入するか環境変数 OPENAI_API_KEY を利用する設計（キーの自動永続化等は行わない）
  - .env の自動ロードは環境変数により無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）

Notes / Migration
- OpenAI を使う機能（ai.news_nlp.score_news / ai.regime_detector.score_regime）は実行前に OPENAI_API_KEY を環境変数で設定するか、api_key 引数で明示的にキーを渡してください。未設定時は ValueError が発生します。
- 自動 .env ロード機能はデフォルトで有効です。CI やテスト環境で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の互換性:
  - executemany に空リストを渡せないバージョン（例: DuckDB 0.10 系）を考慮したコードになっていますが、実際の環境に合わせて動作確認してください。
- データベーススキーマ:
  - ai_scores / market_regime / prices_daily / raw_news / news_symbols / raw_financials / market_calendar 等のテーブルが前提です。初期導入時は schema を準備してください。

Acknowledgements
- 本リリースは内部設計ドキュメント（StrategyModel.md, DataPlatform.md に相当する設計説明）に基づいて実装された初期機能群をまとめたものです。