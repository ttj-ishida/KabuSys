KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/ を準拠

[Unreleased]

- なし

[0.1.0] - 2026-03-27
Added
- 初回リリース: KabuSys 日本株自動売買システムの基礎モジュール群を追加。
- パッケージ公開情報
  - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
  - パッケージ外部公開モジュール候補: data, strategy, execution, monitoring を __all__ に設定。
- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数からの設定読み込みを実装。プロジェクトルートは .git または pyproject.toml を基準に探索して決定（CWD に依存しない）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサは export プレフィックス、クォート内のバックスラッシュエスケープ、inline コメントの扱いなどを考慮した堅牢な実装。
  - protected（OS 環境変数保護）を考慮した上書きロジックを実装。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム設定（env, log_level, is_live/ is_paper/ is_dev）等のプロパティ経由で取得可能。必須変数未設定時の明示的エラーを提供。
- データ関連 (src/kabusys/data/)
  - calendar_management: JPX カレンダー管理と営業日ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar テーブルがない場合は曜日ベースのフォールバックを使用。
    - 夜間バッチ calendar_update_job 関数で J-Quants から差分取得 → 冪等保存（save 側で ON CONFLICT 処理を想定）。
    - 健全性チェック・バックフィル・最大探索日数等の安全対策を実装。
  - pipeline / etl: ETL パイプライン基盤を実装。
    - ETLResult データクラスを定義し、取得件数・保存件数・品質問題リスト・エラーリストを一括管理（to_dict によりシリアライズ可能）。
    - 差分取得・バックフィル・品質チェックを想定した設計（jquants_client/quality と連携）。
  - jquants_client と quality を利用する設計（実処理はクライアント側に委譲）。
- 研究 (research) モジュール (src/kabusys/research/)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離(ma200_dev) を計算。
    - calc_volatility: 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials を用いた PER / ROE を計算（EPS 欠損或いは 0 の場合は None）。
    - DuckDB SQL を用いた実装で、データ不足時の None 処理・ログ出力等を実装。
  - feature_exploration:
    - calc_forward_returns: 指定日からの将来リターン（デフォルト horizons = [1,5,21]）を計算。ホライズン検証（正の整数かつ <=252）を実施。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。有効レコードが少ない場合は None を返す。
    - rank: 平均ランク（同順位は平均ランク）を返すユーティリティ。丸め処理により ties の問題に対処。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - research パッケージは zscore_normalize（data.stats 由来）等の再エクスポートを含む。
- AI / NLP モジュール (src/kabusys/ai/)
  - news_nlp:
    - score_news: raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini, JSON Mode) でバッチ評価して ai_scores に書き込む。
    - タイムウィンドウは JST 基準で前日 15:00 ～ 当日 08:30（内部的には UTC naive に変換）を採用。
    - バッチ処理（_BATCH_SIZE=20）、1銘柄あたりの最大記事数/文字数制限（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）、429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ・リトライ実装。
    - レスポンス検証（JSON 抽出、results 配列、code/score の型チェック、未知コードは無視、数値の有限性チェック）、スコアを ±1.0 にクリップ。
    - 書き込みは部分失敗時に既存スコアを保護するため、スコア取得済みコードのみ DELETE→INSERT の冪等更新を実行。
    - OpenAI 呼び出しを差し替え可能（テスト用に _call_openai_api を patch できる設計）。
  - regime_detector:
    - score_regime: ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、market_regime テーブルへ日次書き込み。
    - マクロニュースは定義済みキーワードでフィルタ（_MACRO_KEYWORDS）、最大件数 20 件。
    - LLM は gpt-4o-mini を使用。API 失敗時はフェイルセーフで macro_sentiment=0.0 を採用。
    - レジームスコアは合成後クリップし、しきい値で label を bull/neutral/bear に分類。
    - DB 書き込みは冪等（BEGIN/DELETE/INSERT/COMMIT）で行い、失敗時は ROLLBACK を試行して例外伝搬。
    - OpenAI 呼び出しのリトライ・5xx の扱い・レスポンス JSON パースの堅牢化を実装。
- 汎用設計／品質
  - 全体を通して「ルックアヘッドバイアス防止」を方針に採用（datetime.today()/date.today() を直接参照しない処理。ただし一部バッチ処理では date.today() を使用）。
  - DuckDB をデータ層に想定した SQL 実装。空パラメータの executemany 回避など DuckDB 固有の注意点に対応。
  - ロギングを各所に挿入し、警告・情報ログを適時出力する設計。
  - テスト容易性を考慮し、OpenAI 呼び出し等の差し替えポイントを用意。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- なし

Notes / 備考
- OpenAI / J-Quants / kabu API 等外部サービスの利用を前提としているため、実行時に対応する API キーやエンドポイント設定が必要です（Settings が必須環境変数を明示）。
- 一部モジュール名（例: monitoring）や外部クライアント実装は本リリースでは参照/想定のみで、実体は別ファイル・外部実装に依存します。必要に応じて実運用前に統合テストを推奨します。