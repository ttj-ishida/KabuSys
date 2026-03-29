# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」のフォーマットに準拠し、セマンティック バージョニングに従います。

[Unreleased]
- 追加予定: 単体テストの整備、OpenAI クライアント抽象化、より細かなメトリクス収集、DuckDB バージョン互換性テスト

---

## [0.1.0] - 2026-03-29

初回公開リリース。以下の主要機能・モジュールを実装。

### Added
- パッケージ構成
  - `kabusys` パッケージを導入。トップレベルで `__version__ = "0.1.0"` を定義し、主要サブパッケージ（`data`, `strategy`, `execution`, `monitoring`）を公開。

- 環境設定管理 (`kabusys.config`)
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読み込みする機能を実装。
  - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - `.env` パーサは `export KEY=val` 形式、シングル/ダブルクォート、エスケープ、インラインコメント（スペース直前の `#` を考慮）に対応。
  - OS 側の既存環境変数は保護（protected）され、`.env.local` による上書きは可能だが OS 変数は上書かれない。
  - `Settings` クラスを提供し、J-Quants / kabuステーション / Slack / DB パスなどの設定にプロパティでアクセス可能。値検証（`KABUSYS_ENV` / `LOG_LEVEL` 等）を含む。
  - 必須環境変数未設定時にはわかりやすい `ValueError` を送出。

- AI 関連機能 (`kabusys.ai`)
  - ニュース NLP スコアリング (`kabusys.ai.news_nlp`)
    - raw_news と news_symbols を集約して銘柄ごとのテキストを作成し、OpenAI（`gpt-4o-mini`）の JSON mode を使って銘柄毎のセンチメントを算出。
    - バッチ処理（デフォルト20銘柄）・トークン増大対策（記事数・文字数制限）を実装。
    - 429（レート制限）、ネットワーク断、タイムアウト、5xx に対する指数バックオフによるリトライを実装。非再試行エラーはスキップして継続するフェイルセーフ設計。
    - レスポンスのバリデーションと数値スコアの ±1.0 クリップ処理を実装。
    - 成果は `ai_scores` テーブルへ（既存レコードは対象コードのみ削除→挿入）書き込む（冪等性を考慮）。
    - `score_news(conn, target_date, api_key=None)` を公開 API として実装。

  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321（225連動）について 200日移動平均乖離とマクロニュースセンチメントを組み合わせて日次レジーム（`bull` / `neutral` / `bear`）を判定。
    - MA200 乖離（重み70%）と LLM マクロセンチメント（重み30%）を合成しスコアを -1..1 にクリップ、閾値でラベル付け。
    - raw_news からマクロキーワードで記事を抽出し、`gpt-4o-mini` で JSON 応答を期待して評価。
    - API エラー時は `macro_sentiment = 0.0` にフォールバックするフェイルセーフ実装。
    - DB へは冪等（BEGIN / DELETE / INSERT / COMMIT）で `market_regime` テーブルへ書き込みを行う。
    - `score_regime(conn, target_date, api_key=None)` を公開 API として実装。

  - AI モジュール固有の設計方針
    - いずれのモジュールもルックアヘッドバイアスを避けるため `datetime.today()` / `date.today()` を直接参照しない設計。
    - OpenAI 呼び出しを行う内部関数は各モジュール内で独立実装し、モジュール間でプライベート関数を共有しないように設計（テスト容易性・結合度低減）。

- データプラットフォーム機能 (`kabusys.data`)
  - カレンダー管理 (`kabusys.data.calendar_management`)
    - `market_calendar` を用いた営業日判定ロジックを提供：`is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`。
    - DB 登録値優先、未登録日は曜日（週末）ベースでフォールバックする一貫した挙動を実装。
    - カレンダー夜間更新ジョブ `calendar_update_job(conn, lookahead_days=...)` を実装（J-Quants クライアント経由で差分取得→保存）。
    - バックフィル、健全性チェック（将来日付異常検知）などを考慮。

  - ETL / パイプライン (`kabusys.data.pipeline`, `kabusys.data.etl`)
    - ETL の結果を表す `ETLResult` データクラスを提供（取得件数、保存件数、品質問題、エラー一覧など）。`to_dict()` をサポート。
    - 差分更新、バックフィル、品質チェックのためのユーティリティを実装方針として確立（J-Quants クライアントと quality モジュールに依存するため、実実装はクライアント側へ委譲）。
    - モジュールの一部を `kabusys.data.__init__` 経由で公開（`ETLResult` の再エクスポートなど）。

- リサーチ機能 (`kabusys.research`)
  - ファクター計算 (`kabusys.research.factor_research`)
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Value（PER, ROE）、Volatility（20日 ATR）、Liquidity（20日平均売買代金、出来高比）等のファクター計算関数を実装。
    - SQL（DuckDB）中心の実装で外部 API を呼ばないことを保証。
    - `calc_momentum`, `calc_volatility`, `calc_value` を公開。

  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - 将来リターン計算（`calc_forward_returns`）、IC（Spearman ランク相関）計算（`calc_ic`）、統計サマリー（`factor_summary`）、ランク化ユーティリティ（`rank`）を実装。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB で完結する実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）
- 設計上の注意点を実装で反映：
  - DuckDB の executemany に関する既知制約（空パラメータの扱い）への対処を実装（空リストのチェック）。
  - OpenAI の JSON mode でも前後余分テキストが混入するケースに対する復元ロジックを追加（最外の {} を抽出してパースを試みる）。

### Security
- OpenAI API キーは `api_key` 引数または環境変数 `OPENAI_API_KEY` から解決される。未設定時は関数が `ValueError` を送出して安全に失敗する仕様。
- `.env` ローダは OS 環境変数を保護（protected set）して、意図せぬ上書きを防止。

### Known limitations / Notes
- DuckDB のバージョン差異（特に配列バインドや executemany の挙動）に依存する箇所があるため、運用環境の DuckDB バージョン確認が必要。
- raw_news.datetime は UTC naive datetime 前提で扱っているため、DB に格納する側で UTC 正規化することが想定される。
- jquants_client（`kabusys.data.jquants_client`）や quality モジュールは外部依存として設計されており、実際の API 呼び出し・保存処理はそれらに委譲される。
- テスト用に内部の OpenAI 呼び出し関数（`_call_openai_api` 等）を patch して差し替えられるように設計されている（ユニットテスト対応を想定）。

---

（注）この CHANGELOG は、提示されたソースコードの構造・コメント・実装方針から推測して作成しています。実際のリリース履歴やコミット単位の変更履歴はリポジトリの Git ログ等を参照してください。