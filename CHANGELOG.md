Keep a Changelog
=================

すべての重要な変更をここに記録します。本ファイルは "Keep a Changelog" の形式に従います。

注: この CHANGELOG は提示されたソースコードから推測して作成したものであり、実際のコミット履歴とは異なる場合があります。

[Unreleased]
------------

- （現時点のソースは初期リリース相当の機能を含むため、主要な変更は 0.1.0 にまとめられています）

0.1.0 - 2026-03-31
------------------

Added
- パッケージ初期リリース。kabusys 名前空間を導入。
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - __all__ に data, strategy, execution, monitoring を公開（将来的なサブパッケージ構成を想定）

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む機能を提供。
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動探索。
  - .env の自動読み込み順序: OS 環境変数 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - 高度な .env パーサ: export プレフィックス、シングル／ダブルクォート内のバックスラッシュエスケープ、行内コメント処理などに対応。
  - 環境変数の保護ロジック: OS 環境変数を protected セットとして上書きを防止。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で安全に取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev のヘルパー

- AI モジュール (src/kabusys/ai)
  - news_nlp モジュール (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し ai_scores テーブルへ書き込み。
    - ニュースウィンドウ: JST 基準で前日 15:00 ～ 当日 08:30（UTC に変換して DB クエリ実行）。calc_news_window を公開。
    - バッチ処理: 最大 20 銘柄/コール、1 銘柄あたり最大 10 記事・最大 3000 文字でトリム。
    - エラーハンドリング: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。リトライ上限超過時はそのチャンクをスキップして継続（フェイルセーフ）。
    - レスポンスバリデーションとスコアクリッピング（±1.0）。
    - テスト容易性: OpenAI 呼び出しのラッパー関数を patch 可能に設計（unittest.mock.patch により差し替え可能）。
  - regime_detector モジュール (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース LLM マクロセンチメント（重み 30%）を合成して日次 market_regime を判定・書き込み。
    - LLM は gpt-4o-mini を使用。記事が無ければ macro_sentiment=0.0 をフォールバック。
    - レジームスコアを clip して regime_label を bull/neutral/bear に分類。
    - DB 書き込みは冪等性を担保（BEGIN / DELETE / INSERT / COMMIT）。
    - API 呼び出しに関するリトライ・例外処理を実装。

- Data モジュール (src/kabusys/data)
  - calendar_management (src/kabusys/data/calendar_management.py)
    - JPX カレンダー管理ロジックを提供（market_calendar テーブルの読取/更新）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - DB 不在時は曜日ベースのフォールバック（週末を非営業日扱い）。
    - 夜間ジョブ calendar_update_job を実装（J-Quants API から差分取得し保存、バックフィル、健全性チェック）。
  - ETL パイプライン (src/kabusys/data/pipeline.py)
    - ETLResult データクラスを実装（パイプラインの集計結果・品質問題・エラー情報を保持）。
    - 差分更新、バックフィル、品質チェック統合の方針に沿ったユーティリティを整備。
  - etl の公開インターフェースをエクスポート（src/kabusys/data/etl.py: ETLResult を再エクスポート）。
  - jquants_client との連携を想定した設計（fetch/save の呼び出し点を実装）。

- Research モジュール (src/kabusys/research)
  - factor_research (src/kabusys/research/factor_research.py)
    - Momentum, Volatility, Value 等の定量ファクターを DuckDB の SQL と Python で計算する関数を実装:
      - calc_momentum: mom_1m/3m/6m、ma200_dev（データ不足時 None を返す）
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（データ不足時 None を返す）
      - calc_value: per, roe（raw_financials から直近の報告を結合）
    - DuckDB を用いたウィンドウ関数、LAG/AVG/ROW_NUMBER を利用した実装。
  - feature_exploration (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 複数ホライズン（例: 1,5,21 日）の将来リターン計算（LEAD を利用）。
    - calc_ic: スピアマンランク相関（ランクは同順位を平均ランクで処理）。
    - factor_summary: 各ファクターに対する count/mean/std/min/max/median を算出。
    - 依存軽量設計: pandas 等に依存せず標準ライブラリのみで実装。
  - research.__init__ で主要関数をエクスポート（zscore_normalize は data.stats から再利用）。

- 設計上の注意・安全策
  - ルックアヘッドバイアス防止: 各モジュールで date.today() / datetime.today() を直接参照しない設計（外部から target_date を注入することで過去データ限定）。
  - DB 書き込みは冪等性を考慮（DELETE → INSERT 等）。部分失敗時に既存データを不必要に消さないようコード上で配慮。
  - DuckDB の executemany に関する互換性問題（空リスト不可）に対応するガードロジックを実装。
  - OpenAI 呼び出し失敗時は例外を投げずフォールバック（中立/スキップ）してパイプライン継続。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- .env 読み込みで読み取り失敗時に警告を出力しプロセスを継続（即時クラッシュを回避）。
- 環境変数の必須項目を明示的にチェックし、未設定時は ValueError を送出して早期に検出（OpenAI キー等）。
- OpenAI キーの取得は引数優先 → 環境変数の順とし、テスト時に明示的に注入可能。

Known issues / Notes / TODO
- 一部ファクター（PBR、配当利回り）は未実装で、将来的な拡張が想定される（calc_value にて注釈あり）。
- OpenAI モデルは gpt-4o-mini を想定しているため、将来的なモデル差し替えでプロンプトやレスポンス処理の調整が必要になる可能性あり。
- news_nlp と regime_detector は独立して OpenAI 呼び出しラッパーを持つ設計だが、重複コードの共通化は将来の改善ポイント。
- 実行には DuckDB と OpenAI Python SDK（および適切な API キー）が必要。
- jquants_client 実装（外部依存）の挿入点は存在するが、実際の API クライアントの実装/設定が別途必要。

References
- 各モジュールの docstring に実装方針や処理フロー・設計判断が記載されています。詳細はソースコード（src/kabusys/**）を参照してください。