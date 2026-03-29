# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

注: この CHANGELOG は与えられたコード内容からの推測に基づき作成しています。

## [0.1.0] - 2026-03-29
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。トップレベルで data / research / ai / その他サブパッケージを公開。
  - バージョン情報を src/kabusys/__init__.py にて __version__ = "0.1.0" で定義。

- 設定・環境変数管理
  - robust な .env ローダを実装（src/kabusys/config.py）。
    - .env/.env.local の自動読み込み（優先順: OS 環境変数 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - export KEY=val 形式対応、クォート値のバックスラッシュエスケープ対応、インラインコメントの取り扱いなど実用的なパーサ実装。
    - override / protected 機能により OS 環境変数の上書きを制御。
  - Settings クラスを提供し、主要設定をプロパティ経由で取得（J-Quants, kabu API, Slack, DB パス, 環境種別・ログレベル等）。
    - KABUSYS_ENV と LOG_LEVEL の値検証を行い、不正値時は ValueError を送出。
    - Path 型で duckdb/sqlite のパスを返すユーティリティ。

- AI (OpenAI) 関連
  - ニュース NLP スコアリングモジュールを追加（src/kabusys/ai/news_nlp.py）。
    - ニュース収集ウィンドウ計算（JST ベース→UTC 変換）。
    - raw_news + news_symbols から銘柄ごとに記事を集約し、銘柄単位で最大記事数・文字数でトリムして OpenAI にバッチ送信。
    - バッチサイズ、トリム制限、リトライ（429/ネットワーク/5xx）・エクスポネンシャルバックオフを実装。
    - レスポンスの厳密な検証とスコアの ±1.0 クリップ。DuckDB へ冪等的に書き込み（DELETE→INSERT）。
    - テスト容易化のため内部の OpenAI 呼び出し関数をモック可能に設計（_call_openai_api をパッチして差し替え）。
  - 市場レジーム判定モジュールを追加（src/kabusys/ai/regime_detector.py）。
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で 'bull'/'neutral'/'bear' を判定。
    - titles の抽出、OpenAI 呼び出し（gpt-4o-mini）、リトライやフェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - 計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - 両モジュールとも OpenAI API キーの注入（引数 or OPENAI_API_KEY 環境変数）をサポートし、未指定時は ValueError を投げる。

- データプラットフォーム（DuckDB ベース）
  - カレンダー管理モジュールを追加（src/kabusys/data/calendar_management.py）。
    - market_calendar テーブルを参照した営業日判定 (is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day) を実装。
    - DB 未登録日への曜日ベースのフォールバック、最大探索日数の制限、バッチ更新ジョブ（calendar_update_job）および J-Quants クライアント経由の差分取得とバックフィル（_BACKFILL_DAYS）を実装。
    - 健全性チェック（未来日付が極端に離れている場合のスキップ）を実装。
  - ETL パイプライン基盤を追加（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）。
    - ETLResult データクラス（実行結果の集約、品質問題・エラー一覧の保持、シリアライズ用 to_dict）を提供。
    - 差分更新用ユーティリティ（テーブル存在チェック・最大日付取得など）を実装。
    - DataPlatform 設計に基づく差分取得/保存/品質チェックの方針を反映。
  - jquants_client / quality 等の外部モジュールをラップする想定で実装。

- リサーチ（ファクター・特徴量探索）
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - モメンタム: mom_1m, mom_3m, mom_6m, ma200_dev（200日MA乖離）を計算する calc_momentum。
    - ボラティリティ/流動性: atr_20, atr_pct, avg_turnover, volume_ratio を計算する calc_volatility。
    - バリュー: per, roe を raw_financials と prices_daily から算出する calc_value。
    - DuckDB SQL を用いた効率的な実装とデータ不足時の None 処理。
  - 特徴量探索モジュールを追加（src/kabusys/research/feature_exploration.py）。
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、入力検証あり）。
    - IC（Spearman ランク相関）計算 calc_ic（入力結合・欠損除外・最小サンプルチェック）。
    - ランク関数 rank（同順位の平均ランク処理、数値丸めによる ties の安定化）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median 計算）。

### 変更 (Changed)
- なし（初回リリースのため新規実装が中心）。

### 修正 (Fixed)
- なし（初回リリース）。

### セキュリティ (Security)
- なし（公開コードからセキュリティ修正は検出できず）。

### 注意事項 / 既知の制限 (Notes / Known issues)
- OpenAI 関連モジュールは外部 API に依存するため、API キー（引数または OPENAI_API_KEY 環境変数）が必須。未設定時は ValueError を送出する設計。
- OpenAI 呼び出しはリトライやフェイルセーフを備えるが、API 料金やレート制限には注意が必要。
- DuckDB のバージョン差異（例: executemany の空リストバインド等）を考慮した実装がなされているが、実行環境の DuckDB バージョンに依存する箇所がある。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行うため、配布後や CWD が異なる場合の挙動に注意。
- テスト容易性のため一部の内部関数（_call_openai_api 等）は unittest.mock.patch で差し替え可能。

### 互換性 (Compatibility)
- 現時点で後方互換性を破る変更（Breaking changes）は存在しない想定。

---
今後のリリースでは、下記のような項目を想定しています（例）:
- モデルパラメータの外部化（設定ファイル経由で閾値や重みを変更可能にする）
- ai_scores / market_regime 等のスキーマ仕様明記とマイグレーションサポート
- テストカバレッジ増強と CI 設定
- J-Quants / kabu クライアントの実装および統合テストの追加

（以上）