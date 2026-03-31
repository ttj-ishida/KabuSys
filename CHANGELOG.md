# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

なお、この CHANGELOG は提供されたコードベースの内容から実装・振る舞いを推測して作成した初期リリース履歴です。

## [0.1.0] - 2026-03-31

### 追加 (Added)
- パッケージ初回リリース: kabusys 0.1.0
  - パッケージ説明: 日本株自動売買システムの基礎ライブラリ群を提供（モジュール群: data, research, ai, config, monitoring 等を想定）。
  - バージョン情報は `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` を設定。

- 環境設定管理モジュール (`kabusys.config`)
  - .env / .env.local ファイルと OS 環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートは `.git` または `pyproject.toml` を探索して決定（CWD に依存しない）。
    - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - `.env` のパースは `export KEY=val`、クォート、エスケープ、コメント処理に対応。
    - `.env.local` は `.env` を上書きする（ただし OS 環境変数は保護）。
  - `Settings` クラスを提供し、以下の主要設定をプロパティで取得可能:
    - J-Quants / kabuステーション API 関連 (例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `KABU_API_BASE_URL`)
    - Slack 関連 (`SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`)
    - DB パス (`DUCKDB_PATH`, `SQLITE_PATH`)
    - 監視関連 (`PID_FILE_PATH`, CPU/Memory/Disk閾値)
    - 環境・ログレベル (`KABUSYS_ENV`, `LOG_LEVEL`) と便利なブールプロパティ (`is_live`, `is_paper`, `is_dev`)
  - 必須設定未定義時は `ValueError` を送出するユーティリティ `_require` を実装。

- AI 関連モジュール (`kabusys.ai`)
  - ニュースセンチメントスコアリング: `kabusys.ai.news_nlp.score_news`
    - OpenAI（gpt-4o-mini）の JSON Mode を用いてニュース（raw_news / news_symbols）を銘柄ごとにスコア化し `ai_scores` テーブルへ書き込む。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を算出する `calc_news_window` を提供（UTC naive datetime を返す）。
    - バッチ処理（最大 20 銘柄/回）、1 銘柄あたりの記事数と文字数の上限、レスポンスの厳格なバリデーション、スコアの ±1 クリップを実装。
    - ネットワークエラー・レート制限・5xx に対する指数バックオフ・リトライを実装。失敗時は安全にスキップし継続（フェイルセーフ）。
    - テスト時に差し替え可能な API 呼び出しラッパー `_call_openai_api`（unittest.mock.patch 用）。
  - 市場レジーム判定: `kabusys.ai.regime_detector.score_regime`
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（'bull' / 'neutral' / 'bear'）を算出・保存。
    - MA 計算はルックアヘッドバイアス防止のため `date < target_date` のデータのみ使用。
    - マクロニュース抽出は `news_nlp.calc_news_window` に基づくウィンドウでキーワードフィルタ（日本・米国等のマクロ用キーワード群）を適用。
    - OpenAI 呼び出しは個別の `_call_openai_api` 実装を持ち、リトライ・エラーハンドリングを実装。API 失敗時は macro_sentiment=0.0 をフォールバック。
    - 結果は `market_regime` テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込む。

- データ基盤モジュール (`kabusys.data`)
  - カレンダー管理: `kabusys.data.calendar_management`
    - JPX カレンダー（market_calendar）を扱うユーティリティ群: 営業日判定（is_trading_day）、次/前営業日取得（next_trading_day / prev_trading_day）、期間内営業日取得（get_trading_days）、SQ 判定（is_sq_day）。
    - DB にカレンダーが無い場合は曜日ベース（土日）でフォールバック。
    - 夜間バッチ: `calendar_update_job` により J-Quants から差分取得して `market_calendar` を冪等更新。バックフィル・健全性チェックあり。
  - ETL パイプライン: `kabusys.data.pipeline` / `kabusys.data.etl`
    - ETL 実行結果を表す dataclass `ETLResult` を提供（取得/保存件数、品質問題、エラー一覧等を保持）。
    - 差分取得、バックフィル、品質チェック（quality モジュール利用）、アイドempotent 保存戦略（ON CONFLICT / executemany）を想定した実装方針。
    - `kabusys.data.etl` は `pipeline.ETLResult` を再エクスポート。
  - DuckDB を用いた SQL ベースのデータ操作に対応（DuckDB 接続を前提）。

- 研究（Research）モジュール (`kabusys.research`)
  - ファクター計算: `calc_momentum`, `calc_value`, `calc_volatility`
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を算出。データ不足時は None。
    - Volatility / Liquidity: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率等を算出。
    - Value: raw_financials から最新の財務データを結合して PER・ROE を算出（EPS が 0/欠損の場合は None）。
    - 全関数は DuckDB の `prices_daily` / `raw_financials` のみ参照し、外部 API へはアクセスしない設計。
  - 特徴量探索: `calc_forward_returns`, `calc_ic`, `rank`, `factor_summary`
    - 将来リターン（任意ホライズン）を LEAD を使って一度のクエリで取得。
    - IC（スピアマンのランク相関）計算、ランク付け（平均ランクで ties 処理）、統計サマリー（count/mean/std/min/max/median）を実装。
    - pandas 等の外部依存を持たない純 Python 実装。

### 改善・設計上の注意点 (Notes / Implementation details)
- ルックアヘッドバイアス防止:
  - AI スコアリング・レジーム判定・ファクター計算等の関数は内部で直接 `date.today()` / `datetime.today()` を参照しない。すべて外部から `target_date` を受け取り、その日の「外側」データを明示的に排除する実装。
- OpenAI API 呼び出し:
  - gpt-4o-mini を前提に JSON Mode を利用。レスポンスの厳格なバリデーションを行い、パース失敗や API エラーはフェイルセーフで処理（多くはスコア 0.0 または該当銘柄スキップ）。
  - テスト用に内部の API 呼び出しを差し替え可能（mock しやすい設計）。
- 冪等性とトランザクション:
  - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT（失敗時は ROLLBACK）で冪等性を確保するパターンを採用。
  - DuckDB の executemany に対する互換性問題（空リスト不可）を考慮したガードを実装。
- エラー・ログと可観測性:
  - 詳細な logger 出力を各モジュールに配置（info/warning/debug/exception）。失敗は原則例外を出さずにログを残して継続する箇所が多い（ETL・AI スコアリング等）。
- 環境変数の必須項目:
  - OpenAI を使う処理は `OPENAI_API_KEY`（または引数 `api_key`）が必須。未設定時は `ValueError` を送出。
  - その他必須: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`（`Settings` のプロパティで `_require` を通して取得）。

### 既知の制約 (Known limitations)
- 一部未実装/未完成想定の機能がある可能性（例: DataPlatform.md / StrategyModel.md に基づく設計を参照する旨のコメント多数）。
- PBR・配当利回り等のバリュー指標は現バージョンでは未実装（calc_value の注記あり）。
- DuckDB バインドの細かい互換性はコード中で考慮されているが、環境差異で追加対応が必要になる可能性あり。
- レスポンスパース時に LLM が仕様外の JSON を返す場合の復元ロジックを入れているが万全ではない（サニティチェック推奨）。

### セキュリティ (Security)
- API キー等の機密情報は環境変数または .env により管理する想定。`.env.local` を使ったローカル上書きをサポート。
- 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。

---

今後のリリースで想定される項目:
- 監視・実行（execution / monitoring）モジュールの実装詳細（現状エクスポート対象に含まれるがソースは提供範囲外）。
- 更なるファクター・リサーチ機能の追加、統合テスト、CI 実行例の追加。
- ドキュメント（使用例、API 仕様、必要な DB スキーマ）およびマイグレーション手順の整備。