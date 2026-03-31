CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います（http://semver.org/）。

Unreleased
----------

（現在未リリースの変更はここに記載します）

[0.1.0] - 2026-03-31
-------------------

Added
- 初回リリース: kabusys パッケージの基本実装を追加。
  - パッケージ公開情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0" と API エクスポート定義。
  - 環境設定:
    - src/kabusys/config.py
      - .env / .env.local ファイルまたは環境変数から設定値を自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
      - 読み込み優先順位: OS 環境 > .env.local > .env。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
      - .env 行パーサ実装（export 形式、クォート、エスケープ、インラインコメントの扱い）。
      - Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス / ログレベル / 環境判定など）。
  - AI（自然言語処理）:
    - src/kabusys/ai/news_nlp.py
      - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し ai_scores テーブルへ保存する score_news を実装。
      - バッチ送信（最大20銘柄）、記事トリム、レスポンスバリデーション、スコアのクリップ（±1.0）、部分書き換え（DELETE → INSERT）による冪等性を確保。
      - エラー耐性: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフとリトライ（最大試行回数を設定）。
      - JSON mode を想定したパースの回復処理（前後の余計なテキストを含む場合でも最外の {} を抽出して復元）。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321（日経225連動型）の200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を算出する score_regime を実装。
      - マクロ記事抽出、OpenAI 呼び出し、リトライ処理、冪等な DB 書き込みを実装。API 失敗時はマクロセンチメントを 0.0 としてフェイルセーフに継続。
      - 設計上ルックアヘッドバイアスを避けるため date 引数ベースで処理（datetime.today() を参照しない）。
  - Research（因子・特徴量探索）:
    - src/kabusys/research/factor_research.py
      - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
      - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。
      - calc_value: raw_financials から最新財務データを取得し PER / ROE を算出。
      - DuckDB を用いた SQL 実装、データ不足時の None ハンドリング。
    - src/kabusys/research/feature_exploration.py
      - calc_forward_returns: 指定ホライズンの将来リターンを一括クエリで算出。
      - calc_ic: スピアマンのランク相関（IC）計算（同順位の平均ランク対応）。
      - factor_summary: 基本統計量（count/mean/std/min/max/median）算出。
      - rank: ランク付けユーティリティ（同順位は平均ランク）。
    - research パッケージ __all__ に主要関数を公開。
  - Data（データパイプライン / カレンダー管理）:
    - src/kabusys/data/pipeline.py
      - ETLResult データクラス（ETL 実行結果管理）、差分取得・保存・品質チェックのためのユーティリティ関数。
      - DuckDB の最大日付取得、テーブル存在チェックなど。
    - src/kabusys/data/etl.py
      - pipeline.ETLResult を再エクスポート。
    - src/kabusys/data/calendar_management.py
      - market_calendar をもとにした営業日判定ユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
      - JPX カレンダーの夜間差分更新ジョブ calendar_update_job（J-Quants API 経由の差分取得・保存・バックフィル・健全性チェック）。
      - DB 登録の有無に応じた曜日ベースのフォールバック、最大探索日数制限等の安全策を実装。
  - パッケージ構成:
    - ai, data, research パッケージの公開インターフェースを整備（__init__.py で関数をエクスポート）。
  - 依存・実装ノート:
    - 全体的に DuckDB を主要なローカルデータストアとして利用。
    - OpenAI Python SDK（OpenAI クライアント）を使用して Chat Completions（JSON Mode）を利用する実装。
    - 設計方針として "ルックアヘッドバイアス防止" を徹底（date 引数駆動、today を直接参照しない）。

Fixed / Hardened
- OpenAI API 呼び出しまわりで堅牢性を確保:
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライロジックを実装（news_nlp と regime_detector 両方で）。
  - APIError の status_code の有無に安全対応し、5xx 判定に応じたリトライ制御。
  - レスポンスの JSON パース失敗やフィールド欠落に対するフォールバック（ログ出力してスコア 0.0 またはスキップ）を行うことで処理の継続性を向上。
- DuckDB に対する互換性処理:
  - executemany に空リストを与えない防御（DuckDB 0.10 の制約に対応）。
  - テーブル存在チェック・日付値変換ユーティリティを追加し安定性を改善。
- .env 読み込み:
  - OS 環境変数保護（protected set）を導入し .env の上書き制御を実装。

Notes
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用（未設定時は ValueError を送出）。
- 一部モジュール（例: jquants_client）は参照されるがこの差分に含まれる実装は外部モジュールに依存。
- 設計上、重要な挙動（時刻窓や DB 書き込み）は冪等性とルックアヘッド防止を意識して実装されています。

Acknowledgements
- 本リリースはデータ品質・リスク軽減を重視した設計方針に基づいています。将来的なバージョンでは strategy / execution / monitoring 部分の実装拡張や API クライアントの差し替えに対応予定です。