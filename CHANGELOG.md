# Changelog

すべての変更は「Keep a Changelog」準拠で記載しています。  
現在のパッケージバージョン: 0.1.0

注意: この CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。

## [Unreleased]

- （現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-01

初期公開リリース。日本株自動売買プラットフォームのコアデータ処理、リサーチ、AI 助言（ニュース NLP / 市場レジーム判定）、および環境設定を含む基盤機能を提供します。

### Added

- パッケージ構成
  - トップレベルパッケージ `kabusys` を追加。公開 API はサブパッケージ `data`, `strategy`, `execution`, `monitoring` を想定（strategy / execution / monitoring の具体実装は本コードベースでは部分的または未実装）。

- 環境設定管理（kabusys.config）
  - .env ファイル（.env, .env.local）または環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml を起点）により、カレントワーキングディレクトリに依存しない読み込みを実現。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサを実装（コメント、export 形式、クォート内のバックスラッシュエスケープ等に対応）。
  - 必須設定を取得するヘルパー `_require` と、アプリ設定をラップする `Settings` クラスを提供。
  - 主な必須環境変数:
    - `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`
    - （OpenAI を利用する機能は `OPENAI_API_KEY` を参照）

- データ / ETL（kabusys.data）
  - ETL パイプライン型 `ETLResult` を公開（kabusys.data.etl で再エクスポート）。
    - ETL 実行結果の集約、品質問題（quality.QualityIssue）やエラー一覧を保持。
  - ETL 処理の骨組み（kabusys.data.pipeline）
    - 差分更新、backfill、品質チェックとの連携ができる設計。
    - DuckDB を想定した DB 操作ユーティリティ（テーブル存在チェック、最大日付取得等）。
  - 市場カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの差分取得ジョブ（calendar_update_job）を実装。
    - 営業日判定ユーティリティ群を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録データ優先、未登録日は曜日ベースでフォールバックする堅牢な設計。
    - バックフィル、先読み、健全性チェックを実装。

- AI / NLP（kabusys.ai）
  - ニュースセンチメント（銘柄別）スコア化（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとに前日15:00 JST～当日08:30 JST のウィンドウを対象にスコアを生成。
    - OpenAI（gpt-4o-mini）の JSON Mode を利用してバッチで評価（1リクエストで最大 _BATCH_SIZE=20 銘柄）。
    - レスポンスのバリデーション、スコアの ±1.0 クリップ、部分失敗時の部分書き換え戦略（DELETE → INSERT）を採用して既存データを保護。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフのリトライ実装。
    - テスト用に _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を組み合わせ、日次で市場レジーム（bull / neutral / bear）を判定して market_regime テーブルへ冪等書き込み。
    - News NLP の記事集約関数 calc_news_window を利用して同様の時間窓でニュースを取得。
    - OpenAI 呼び出しのリトライ / フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス防止のため、date 比較は厳密に target_date 未満／半開区間を利用。

- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日 ATR、相対 ATR）、Value（PER, ROE）などを DuckDB 上の prices_daily / raw_financials から計算する関数を実装。
    - 欠損データに対する扱い（十分な履歴が無ければ None）を明確にしている。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず、純標準ライブラリ + DuckDB SQL で実装。

- ロギングと安全性
  - 各モジュールにおける詳細な logger 出力を追加（処理状況・警告・例外情報）。
  - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を保つ設計。
  - 外部 API 周りはフェイルセーフ設計（部分失敗で例外を投げず継続する戦略を多用）。

### Changed

- 初回リリースのため「変更」はなし（新規追加のみ）。将来的な API 変更に注意。

### Fixed

- 初回リリースのため「修正」はなし。

### Security

- OpenAI API キーや各種トークンは環境変数で管理。自動ロード機能があるため、.env 管理時の権限管理に注意してください。
- .env の上書き保護（protected set）を実装し、OS 環境変数が意図せず上書きされないよう配慮。

### Known issues / Notes（既知の注意点・制約）

- pipeline._get_max_date の末尾が不完全（ファイル切断／タイポの痕跡: "return date.fro" のような未完の行）が存在します。現状ではその関数が正しく動作しない可能性があり、リリース前に修正が必要です（ソースの続きが欠けている）。
- strategy / execution / monitoring サブパッケージはトップレベルの __all__ に含まれていますが、今回提供されたコードセットではこれらのモジュール群が未公開または部分的です。取引実行や監視ロジックは別途実装が必要です。
- 実行環境依存:
  - DuckDB、OpenAI SDK（openai）、および J-Quants クライアント（kabusys.data.jquants_client で参照）に依存します。これらのクライアント実装・バージョン互換性に注意してください。
- 時刻取り扱い:
  - ニュースウィンドウは JST を基準に計算し、DB として UTC naive datetime を使用する設計です。保存済みデータが他のタイムゾーン／タイムスタンプ仕様の場合は整合性確認が必要です。
- テスト支援:
  - OpenAI 呼び出しはモジュール内の _call_openai_api をモック可能な作りになっているため、ユニットテストで外部 API をシミュレートしやすく設計されています。
- フェイルセーフ挙動:
  - LLM 呼び出し失敗時はマーケットセンチメントを 0.0 やスコア無しとして継続するため、API 側の問題によりスコアリングが保守的（中立寄り）になります。

### Migration / Upgrade notes

- 必須環境変数（デプロイ前に設定してください）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI を利用する場合は OPENAI_API_KEY（news_nlp / regime_detector / その他 AI 機能）
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。パッケージ配布環境や CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化することを推奨します。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）に依存しています。初回セットアップ時は必要なテーブル定義・インポート処理を準備してください。

---

発行者: kabusys コード読み取りに基づく推測的な変更履歴（自動生成）  
注: 実際のリリースノート・コミット履歴と差異がある場合があります。