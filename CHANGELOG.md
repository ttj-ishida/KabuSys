# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-04
初回公開リリース。以下の主要機能・モジュールを追加しました。

### 追加
- 基本パッケージ情報
  - パッケージ名: kabusys、バージョン 0.1.0 を追加。

- 環境設定 / 初期化
  - 自動 .env 読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。テスト等で自動読み込みを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
  - .env パーサー実装:
    - `export KEY=val` 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - クォートなしの行に対してインラインコメント（#）の扱いを適切に処理。
  - Settings クラスを追加し、環境変数の取得とバリデーションを集約。
    - 必須環境変数の取得（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - データベースパスのデフォルト（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db）。
    - 監視用の閾値やファイルパス（PID・kill フラグ）を設定可能。
    - KABUSYS_ENV と LOG_LEVEL に対する許容値チェック（値が不正な場合は ValueError）。

- AI（自然言語処理）モジュール
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に、銘柄ごとに記事を集約して OpenAI（gpt-4o-mini、JSON Mode）でセンチメントを評価し ai_scores テーブルに書き込み。
    - 時間ウィンドウ計算（JST基準 → UTC naive datetime）を提供する calc_news_window を実装。
    - バッチサイズ制御（1 API コールあたり最大 20 銘柄）、1銘柄あたりの最大記事数と文字トリムを実装。
    - レスポンス検証ロジック（JSON 抽出・構造検証・数値チェック・既知コードの照合）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ（リトライ）を実装。失敗時は安全にスキップ（例外を上げない）。
    - DuckDB 0.10 の executemany の制約を考慮した空リストチェック。
    - 公開関数: score_news(conn, target_date, api_key=None)
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して日次で market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出のためのキーワードリストと最大取得件数を設定。
    - OpenAI 呼び出しは独立実装、retry/backoff と 5xx の判定を実装。API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - 公開関数: score_regime(conn, target_date, api_key=None)

- データ処理（Data Platform）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー管理機能（市場営業日判定・次/前営業日取得・期間内営業日リスト・SQ 日判定）。
    - market_calendar テーブルが存在しない場合は曜日ベース（土日非営業日）でフォールバック。
    - calendar_update_job により J-Quants から差分取得して冪等保存（バックフィル・健全性チェックを含む）。
  - ETL パイプライン関連
    - ETLResult データクラス（kabusys.data.pipeline.ETLResult）を追加し、ETL の結果を構造化して返却可能に。
    - pipeline モジュールで差分更新、保存（jquants_client 経由の idempotent 保存）、品質チェック（quality モジュール）を行う設計。
    - デフォルトのバックフィルや最小データ日などの定数を設定。
    - 内部ユーティリティ: テーブル存在確認、最大日付取得など。

- リサーチ / ファクター計算（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算する calc_momentum を実装。
    - Volatility / Liquidity: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算する calc_volatility を実装。
    - Value: raw_financials から最新財務情報を取得して PER / ROE を計算する calc_value を実装。
    - 全関数は prices_daily / raw_financials のみ参照し、外部 API にはアクセスしない設計。
    - 過去データ不足時は None を返す安全設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)（デフォルト horizons=[1,5,21]）。
      - LEAD/LAG を利用した1クエリ取得、ホライズン入力チェック（正の整数、最大252）。
    - IC（Information Coefficient）計算: calc_ic（スピアマンランク相関を実装、レコード不足時は None）。
    - rank ユーティリティ（同順位は平均ランクとして処理）。
    - factor_summary: 各ファクターに対する count/mean/std/min/max/median を算出する統計サマリー関数。

### 改良 / 設計上の注意点
- ルックアヘッドバイアス防止
  - AI モジュール、リサーチ関数ともに datetime.today() / date.today() を直接参照せず、明示的な target_date を受け取る設計によりルックアヘッドを防止。
  - DB クエリにおいても target_date 未満（排他）や date = ? を適切に使用して将来データ参照を回避。

- 冪等性と部分失敗耐性
  - DB への書き込みは冪等操作（DELETE → INSERT、ON CONFLICT の想定）を前提としており、部分失敗時に既存データを不必要に消さないよう配慮（ai_scores や market_regime の扱い）。
  - トランザクション（BEGIN / COMMIT / ROLLBACK）で整合性を確保。

- エラーハンドリング
  - 外部 API（OpenAI、J-Quants）呼出し時は 429・ネットワーク断・タイムアウト・5xx を意識したリトライ戦略（指数バックオフ）を実装。非再試行エラーやパース失敗はログに記録してフェイルセーフにフォールバック。
  - JSON パースでは前後テキスト混入ケースの復元ロジックを備え、厳密な応答検証を行う。

- DuckDB 互換性への配慮
  - executemany の空リスト制約等、DuckDB の既知の挙動に対する回避処理を実装。

### 既知の制限 / TODO
- ai モジュールは OpenAI の有効な API キー（OPENAI_API_KEY または api_key 引数）が必須。キーが未設定の場合は ValueError を発生させる。
- 現バージョンでは PBR・配当利回りなど一部バリューファクターは未実装。
- jquants_client、quality モジュール等の外部連携実装（API クライアントの具象実装）は別途提供される前提。
- テスト用フック（_call_openai_api の差し替え等）は設計に含めているが、モック/テストケースは付属していない。

### 互換性（Breaking Changes）
- 初回リリースのため破壊的変更は無し。

---

参考: Keep a Changelog の方針に従い、今後の変更はこのファイルで管理します。