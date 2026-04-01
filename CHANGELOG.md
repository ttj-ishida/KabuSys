# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

現在の安定版: [0.1.0] - 2026-04-01

<!--
フォーマット例:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed: 削除
- Deprecated: 非推奨
- Security: セキュリティ関連
-->

## [Unreleased]
- なし

## [0.1.0] - 2026-04-01

### Added
- パッケージ基盤
  - 初期リリースとして kabusys パッケージを導入。トップレベルで data / strategy / execution / monitoring を公開。
  - バージョン情報: `kabusys.__version__ == "0.1.0"`。

- 設定・環境管理
  - 環境変数/設定読み込みモジュール (`kabusys.config`) を実装。
    - プロジェクトルートを `.git` または `pyproject.toml` を基準に探索し、`.env` および `.env.local` を自動読み込み（環境変数が優先される）。
    - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。
    - `.env` のパースは
      - `export KEY=val` 形式対応、
      - シングル/ダブルクォート内のバックスラッシュエスケープ対応、
      - インラインコメント処理（クォートあり／無しで適切に扱う）を実装。
    - `Settings` クラスでアプリケーション設定をプロパティ化（J-Quants / kabu / Slack / DB パス /監視閾値 / 環境判定）。
    - 必須環境変数未設定時は `ValueError` を投げる `_require` を提供。

- AI（自然言語処理）関連
  - ニュースベースのセンチメントスコアリング (`kabusys.ai.news_nlp`) を実装。
    - 指定タイムウィンドウ（JST基準）に基づき raw_news と news_symbols を集約し、銘柄ごとにテキストを結合して OpenAI（gpt-4o-mini）へ送信、JSON モードでレスポンスをパースして `ai_scores` テーブルへ書き込み。
    - バッチサイズ、トークン肥大化対策、最大記事数/文字数の上限、チャンク処理などを導入。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライと、その他エラー時は安全にスキップするフェイルセーフ設計。
    - レスポンスの堅牢なバリデーション（JSON 抽出・キー検査・数値検証・未知コード無視）を実装。
  - 市場レジーム判定モジュール (`kabusys.ai.regime_detector`) を実装。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日別に `market_regime` テーブルへ冪等的に書き込み。
    - OpenAI 呼び出しは独立実装で、リトライ/エラーハンドリングを備える。記事が無い場合はマクロセンチメントを 0.0 にフォールバック。
    - ルックアヘッドバイアス防止のため、明示的な日付引数を用い、DB クエリは target_date 未満のデータのみ参照する設計。

- リサーチ・ファクター計算
  - `kabusys.research` 名前空間を追加。以下を提供：
    - ファクター計算: `calc_momentum`, `calc_value`, `calc_volatility`（prices_daily / raw_financials を参照）。
      - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER, ROE）を計算。
      - DuckDB のウィンドウ関数を活用し、データ不足時には None を返す扱い。
    - 特徴量探索: `calc_forward_returns`, `calc_ic`, `factor_summary`, `rank`
      - 将来リターンの計算（任意ホライズン、入力検証あり）、スピアマン IC（ランク相関）、基本統計量集計を提供。
      - 外部ライブラリに依存せず標準ライブラリと DuckDB で実装。

- データプラットフォーム・ETL
  - `kabusys.data.pipeline` に ETL 関連処理と `ETLResult`（データクラス）を導入。ETL の収集結果、品質チェック情報、エラー概要を保持。
  - `kabusys.data.etl` で `ETLResult` を公開再エクスポート。
  - カレンダー管理 (`kabusys.data.calendar_management`) を実装。
    - JPX カレンダー同期（J-Quants から差分取得）ロジック、営業日判定 (is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day) を提供。
    - market_calendar がない場合は土日ベースでフォールバック。DB 登録値を優先する一貫した挙動。
    - 夜間バッチ `calendar_update_job` を実装（バックフィル、健全性チェック、冪等保存）。
  - DuckDB を前提とした安全なトランザクション（BEGIN/DELETE/INSERT/COMMIT と失敗時の ROLLBACK 保護）を各所で採用。

### Fixed
- 初期リリースのため特定の既知バグ修正履歴はなし（ただし下記に注意点あり）。

### Security
- 環境変数自動読み込みで OS 環境変数を保護するため、.env 読み込み時に現在の os.environ のキー集合を protected として扱い、`.env.local` を上書き可能な挙動を制御。
- OpenAI API キーや Slack トークン等の必須情報について、未設定時は例外を投げることで誤動作を防止。

### Known issues / Notes（注意事項）
- pipeline._get_max_date の実装が不完全に見える箇所（ファイル末尾付近に `return date.fro` のような断片が存在）があります。これは構文エラーとなり、当該関数実行時に問題を引き起こす可能性があります（要修正）。
- 一部モジュールは外部モジュール（`kabusys.data.jquants_client` や `kabusys.data.quality`）に依存しており、これらのクライアント実装がないと ETL / カレンダー更新等は動作しません。
- テスト用フックとして各モジュールは OpenAI 呼び出し関数を patch 可能（unit test 用に _call_openai_api を差し替えられることを想定）。
- 現在の実装では gpt-4o-mini の JSON Mode を利用する前提のため、API の応答仕様変更や利用制限によりパース/処理が影響を受ける可能性があります。
- デフォルト DB パスや PID ファイルパスは相対パス（data/...）が設定されているため、デプロイ環境では環境変数での上書きを推奨。

### Internal / Implementation notes
- 全体的に「ルックアヘッドバイアス防止」を設計方針としており、日時参照は外部から与えた target_date を基準に行う設計（datetime.today() 等の直接参照を避ける）。
- DuckDB の互換性（executemany の空リスト制約や list バインドの不安定さ）を考慮した実装になっている。
- AI モジュールは部分失敗を許容し、可能な限り他データを保護する（例: ai_scores は取得成功コードのみ置換）。

---

過去の変更（リリース履歴）が将来的に増えた場合は、各リリースごとにこのファイルを更新してください。問題のある箇所（特に pipeline._get_max_date）については優先的な修正を推奨します。