CHANGELOG
=========

すべての重要な変更を記録します。本ファイルは "Keep a Changelog" の慣例に従っています。
各リリースは意味のある変更点（Added / Changed / Fixed / Removed 等）を日本語で記載しています。

[0.1.0] - 2026-04-03
--------------------

Added
- 初回公開。KabuSys の基本モジュール群を追加。
  - パッケージ初期化:
    - src/kabusys/__init__.py に __version__ = "0.1.0" と __all__ を定義。
  - 環境・設定管理:
    - src/kabusys/config.py
      - .env ファイルおよび環境変数読み込み機能を実装（自動ロード: OS 環境 > .env.local > .env）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロードの無効化対応。
      - .env パースの堅牢化: コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
      - _load_env_file にて override と protected（OS 環境変数保護）をサポート。
      - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB/監視/システム設定をプロパティ経由で取得。
      - KABUSYS_ENV と LOG_LEVEL のバリデーション（許容値チェック）を実装。
  - AI（自然言語処理）:
    - src/kabusys/ai/news_nlp.py
      - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメント（-1.0〜1.0）を算出。
      - ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を実装（calc_news_window）。
      - バッチ処理（最大 20 銘柄/コール）、記事数・文字数のトリム、結果バリデーション、スコアのクリップ、部分書き込み（取得できたコードのみ DELETE→INSERT）を実装。
      - API 呼び出しは 429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフでリトライ。テスト用に _call_openai_api を差し替え可能。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とニュースのマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出・保存。
      - prices_daily と raw_news を参照し、OpenAI（gpt-4o-mini）を用いてマクロセンチメントを算出。API 失敗時はフェイルセーフで macro_sentiment=0.0。
      - レジーム値のクリップ、閾値判定、および market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時の ROLLBACK 処理）を実装。
  - Research（因子・特徴量解析）:
    - src/kabusys/research/factor_research.py
      - Momentum / Volatility / Value 等の定量ファクター計算関数を実装:
        - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None を返す）。
        - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率。
        - calc_value: PER/ROE（raw_financials を参照、EPS が 0/欠損の場合は None）。
      - DuckDB の窓関数を活用し、価格・財務データのみ参照する安全な実装。
    - src/kabusys/research/feature_exploration.py
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
      - calc_ic: スピアマンのランク相関（Information Coefficient）を計算するユーティリティ。
      - rank: 同順位は平均ランクで処理するランク関数（丸めによる ties を考慮）。
      - factor_summary: count/mean/std/min/max/median の統計サマリーを計算。
    - research パッケージから主要 API を再エクスポート（zscore_normalize 等）。
  - Data（データ基盤）:
    - src/kabusys/data/calendar_management.py
      - JPX カレンダー管理: market_calendar を基に営業日判定（is_trading_day）, next/prev_trading_day, get_trading_days, is_sq_day を提供。
      - DB データがない場合は曜日ベースのフォールバック（祝日情報未取得時でも一貫した挙動）。
      - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィルと健全性チェック実装。
    - src/kabusys/data/pipeline.py
      - ETL パイプライン基盤（差分取得、保存、品質チェックの流れ）と ETLResult データクラスを実装。
      - ETLResult で取得/保存数、品質問題、エラー概要を構造化して返却。has_errors / has_quality_errors / to_dict を提供。
    - src/kabusys/data/etl.py
      - pipeline.ETLResult を再エクスポート。
    - データ操作は DuckDB を前提に実装。
  - テスト性・堅牢性向上:
    - OpenAI 呼び出しをモジュールローカルの _call_openai_api に集約し、テスト時に patch により差し替えやすく実装。
    - API 呼び出し・DB 書き込み失敗時のフォールバックやリトライ、ログ出力、トランザクションロールバックの整備。
    - ルックアヘッドバイアス防止のため、各処理で datetime.today()/date.today() を不用意に参照しない設計方針を明示。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Removed
- 初版のため該当なし。

注記（設計上の重要ポイント）
- DuckDB を主要なローカル DB として想定しており、クエリ実行および executemany の挙動（空リスト不可など）に配慮した実装が行われています。
- OpenAI の出力は JSON モードを利用する想定だが、JSON の前後に余計なテキストが混ざる場合の復元処理も実装しています。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に探索するため、CWD に依存せずパッケージ配布後も適切に動作します。
- 環境変数の必須チェックは _require を通じて ValueError を送出し明示的に失敗させます。

今後の課題（参考）
- 発注/実行（execution）や監視（monitoring）モジュールの詳細実装・ドキュメント化。
- CI テスト用のモックや e2e テストケースの整備（特に OpenAI/J-Quants 呼び出し部分）。
- パフォーマンス監視やメトリクス出力の追加（ETL 大量データ時の挙動確認）。

---