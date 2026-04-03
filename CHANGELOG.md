# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを採用します。

## [Unreleased]

## [0.1.0] - 2026-04-03

初期リリース。本リリースでは日本株自動売買／データ基盤・リサーチ・AI補助の基盤的機能を実装しています。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
  - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ で定義。

- 設定/環境変数管理 (src/kabusys/config.py)
  - .env / .env.local 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env パーサーはコメント、export プレフィックス、シングル/ダブルクォート、エスケープをサポート。
  - OS 環境変数を保護する機能（protected set）および override オプションを提供。
  - 自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - Settings クラスを実装し、J-Quants / kabu / LINE / データベース / 監視 / システム設定をプロパティで取得。
  - 必須値未設定時の _require による ValueError 発生や env/log_level の検証を実装。
  - デフォルトパスや監視閾値等のデフォルト値を提供（例: DUCKDB_PATH, PID_FILE_PATH 等）。

- AI ニュース NLP（センチメント） (src/kabusys/ai/news_nlp.py)
  - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON mode を使ってセンチメントを算出。
  - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST）と calc_news_window 実装。
  - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの記事数・文字数上限によるトリム機構。
  - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装。
  - レスポンスの厳密なバリデーションとスコアの ±1.0 クリップ。
  - DB への冪等書き込み（対象コードのみ DELETE → INSERT）により部分失敗時の保護。
  - 公開関数: score_news(conn, target_date, api_key=None)。

- AI 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF 1321（日経225連動）200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定。
  - DuckDB からのデータ取得、マクロキーワードによるニュース抽出、OpenAI 呼び出し（gpt-4o-mini）を実装。
  - LLM 呼び出しのリトライ戦略、API 失敗時は macro_sentiment=0.0 とするフェイルセーフを採用。
  - 計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - 公開関数: score_regime(conn, target_date, api_key=None)。

- データプラットフォーム / ETL（src/kabusys/data/*）
  - ETL 結果を表す ETLResult データクラスを実装および再エクスポート（src/kabusys/data/etl.py, pipeline.py）。
    - ETL 実行統計、品質問題（quality.QualityIssue）、エラー概要、ヘルパー to_dict、has_errors/has_quality_errors を提供。
  - マーケットカレンダー管理モジュールを実装（src/kabusys/data/calendar_management.py）
    - market_calendar を元に is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB 未取得時の曜日ベースフォールバック、最大探索日数ガード、バックフィル／健全性チェック、夜間バッチ更新ジョブ calendar_update_job を実装。
    - J-Quants クライアント呼び出しを想定（jquants_client を利用）。
  - ETL パイプライン基盤（差分取得・保存・品質チェック、src/kabusys/data/pipeline.py）
    - 差分更新ロジック、バックフィル、品質チェックを組み込む設計。DuckDB テーブル存在確認や最大日付取得ユーティリティ等を実装。
    - デフォルトの最小データ日やカレンダー先読み日数などの定数を定義。

- リサーチ / ファクター計算 (src/kabusys/research/*)
  - factor_research.py: Momentum / Volatility / Value / Liquidity 等の定量ファクターを実装。
    - calc_momentum(conn, target_date): mom_1m/3m/6m、ma200_dev（200日MA乖離）を計算。
    - calc_volatility(conn, target_date): 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date): 最新財務データ（EPS/ROE）と株価から PER, ROE を計算。PBR・配当利回りは未実装。
  - feature_exploration.py:
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を計算。
    - rank(values): 同順位は平均ランクで扱うランク変換。
    - factor_summary(records, columns): count/mean/std/min/max/median を算出。
  - 研究向けユーティリティを kabusys.research パッケージとしてエクスポート（zscore_normalize は data.stats から再利用）。

### 変更 (Changed)
- なし（初期リリース）

### 修正 (Fixed)
- なし（初期リリース）

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### 既知の制限・設計上の注意
- OpenAI の利用は環境変数 OPENAI_API_KEY または関数引数で API キーを渡す必要がある（未設定時は ValueError）。
- ニュース・レジーム処理はいずれもルックアヘッドバイアス防止のために内部で date.today()/datetime.today() を参照しない設計。
- 一部機能は外部 J-Quants クライアント（jquants_client）に依存するため、実行環境でのクライアント実装が必要。
- PBR・配当利回り等のバリュー指標は本バージョンでは未実装。
- DuckDB に対して executemany に空リストを渡せないバージョン依存の取り扱い（空チェックを実装）。
- market_calendar がない場合は曜日ベースのフォールバックを使用する点に注意（完全な祝日情報が必要な場合は calendar_update_job を実行）。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの実装拡充（発注ロジック、モニタリングプロセス管理）
- リサーチ機能のパフォーマンス改善および追加ファクター
- OpenAI 呼び出しの非同期化やコスト削減のための最適化

（詳細な API 仕様・使用例は各モジュールの docstring を参照してください）