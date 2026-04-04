# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用しています。

なお、この CHANGELOG は提示されたコードベースの内容から推測して作成しています。

## [Unreleased]

（現在未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-04-04

初回リリース — KabuSys: 日本株自動売買・データ基盤・リサーチ用ユーティリティ群

### Added
- パッケージ基盤
  - パッケージメタ情報: `src/kabusys/__init__.py` にバージョン 0.1.0 と公開 API（data, strategy, execution, monitoring）を追加。

- 環境設定管理
  - `kabusys.config`:
    - .env ファイル（.env / .env.local）をプロジェクトルート（.git または pyproject.toml を基準）から自動読込する機能。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` 環境変数で自動ロードを無効化可能。
    - 行のパースにおいて `export KEY=val` 、クォート、エスケープ、インラインコメント処理に対応する堅牢な .env パーサを実装。
    - `Settings` クラスを提供し、アプリケーションで利用する各種設定（J-Quants、kabuステーション、LINE、データベースパス、監視閾値、環境種別、ログレベルなど）をプロパティとして取得可能。
    - 必須環境変数用の検証メソッド（未設定時は ValueError を送出）。
    - `KABUSYS_ENV` と `LOG_LEVEL` の許容値チェックを実装。

- AI / NLP
  - `kabusys.ai.news_nlp`:
    - raw_news と news_symbols を集約して銘柄別にニューステキストを作成し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントを算出。
    - バッチ送信（最大 20 銘柄/チャンク）、1 銘柄当たりの記事数・文字数上限、レスポンスバリデーション、スコアの ±1.0 クリッピング、部分成功時の DB 書き換え（DELETE → INSERT）を実装。
    - レートリミット・ネットワーク断・タイムアウト・5xx に対する指数バックオフとリトライロジックを実装。
    - JSON モードの出力で前後余計テキストが混入した場合に最外側の {} を抽出する耐性処理を実装。
    - テスト用に OpenAI 呼び出しを差し替えられるフック（関数）を用意。

  - `kabusys.ai.regime_detector`:
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - `score_regime` により、ma200_ratio の算出、マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）、スコア合成、`market_regime` テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実施。
    - API 失敗時はフェイルセーフとして macro_sentiment=0.0 を採用する挙動を採用。
    - OpenAI 呼び出しに対するリトライ（429/ネットワーク/タイムアウト/5xx）とログ出力を実装。

- データプラットフォーム / ETL / カレンダー
  - `kabusys.data.calendar_management`:
    - JPX カレンダー管理（market_calendar テーブル）の取得・判定ロジックを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といったユーティリティを実装。
    - DB 登録がない場合は曜日（平日）ベースのフォールバックを行う設計（DB 登録値があればそれを優先）。
    - 夜間バッチ更新ジョブ `calendar_update_job` を実装（J-Quants クライアント経由で差分取得 → 保存、バックフィル・健全性チェックを含む）。
  - `kabusys.data.pipeline`:
    - ETL のための高水準パイプライン設計および `ETLResult` 型を実装（差分取得、保存、品質チェックの結果格納）。
    - ETL 実行結果を辞書に変換する `to_dict` を提供。
    - DuckDB を利用したテーブル存在チェックや最大日付取得などのユーティリティを実装（差分更新・バックフィル方針を備える）。
  - `kabusys.data.etl`:
    - `ETLResult` を再エクスポート。

- リサーチ / ファクター
  - `kabusys.research.factor_research`:
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER、ROE）など複数のファクター計算関数を実装。
    - DuckDB の SQL とウィンドウ関数を併用し、必要なデータ不足時の None 返却など堅牢に実装。
  - `kabusys.research.feature_exploration`:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク付けユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリのみで完結する実装。
  - `kabusys.research.__init__` で主要 API を公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キー等の機密情報は環境変数で取得する設計（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。必須設定が未達成のときは明示的にエラーを出す。
- .env 自動読み込みはデフォルトで有効だが、CI/テスト用途に `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。

### Notes / Design Decisions（重要な実装上の注意）
- ルックアヘッドバイアス防止:
  - AI モジュール（news_nlp, regime_detector）やファクター計算で、内部的に datetime.today()/date.today() を参照せず、呼び出し側からの target_date に依存する設計になっています。
  - DB クエリでは target_date 未満や半開区間等の条件を厳密に使い、将来情報の混入を防止。
- フェイルセーフ:
  - OpenAI 呼び出し失敗時は例外を上位に投げず、スコアを 0.0 にフォールバックするなど処理継続を優先する箇所があります（ログで警告）。
- DB 書き込みは冪等性を重視:
  - ai_scores / market_regime などへの書き込みは一度 DELETE してから INSERT するスタイルで、部分失敗時に既存データを不必要に消去しない工夫がされています。
  - DuckDB の executemany に関する仕様差（空リスト不可）に配慮した実装が含まれます。
- OpenAI 呼び出し:
  - gpt-4o-mini を前提とした JSON mode（response_format={"type":"json_object"}）を利用。
  - SDK の例外型の違いに対する互換性確保（status_code の存在チェック等）やリトライ増分バックオフを実装。
- カレンダー処理:
  - market_calendar がまばらにしかない場合にも next/prev/get_trading_days が一貫した結果を返すよう DB優先→曜日フォールバックの方針を採用。
  - 夜間更新ジョブにてバックフィルと最大探索・健全性チェックを実装。

### 開発者向け注意事項 / 移行時のヒント
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（使用機能に応じて）や OPENAI_API_KEY（AI 機能を利用する場合）は必ず設定してください。未設定時は該当 API 呼び出しで ValueError が発生します。
- .env の自動読み込みはパッケージの配置パス（.git または pyproject.toml があるディレクトリ）を基準に実行されます。配布後やテスト時は挙動に注意してください（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定）。
- DuckDB を用いたクエリや executemany の挙動に依存する箇所があります。DuckDB のバージョン互換性に注意してください（特に executemany に空リストを渡すとエラーになる点など）。
- OpenAI クライアント呼び出しは内部でラップしているため、テスト時はモック差し替えがしやすい設計になっています（関数名に対して unittest.mock.patch で差し替え可能）。

---

（他のリリースや修正が発生した場合は本ファイルを更新してください）