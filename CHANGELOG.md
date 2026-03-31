# CHANGELOG

すべての重要な変更は Keep a Changelog の形式で記録します。  
このプロジェクトの初期リリースは以下の内容を含みます。コードから仕様・設計方針を推測して記載しています。

全般的な注意
- 日付はこの CHANGELOG 作成時点 (2026-03-31) を用いています。実際のリリース日を適宜更新してください。
- 環境変数（特に OpenAI / J-Quants / kabu ステーション / Slack 関連）は多数必須です。詳細は各モジュールのドキュメントおよび .env.example を参照してください。

## [0.1.0] - 2026-03-31

### Added
- パッケージ基盤
  - パッケージエントリポイント `kabusys` を追加。バージョンは `0.1.0`。
  - 公開サブパッケージ: data, strategy, execution, monitoring（__all__ に設定）。

- 設定管理 (`kabusys.config`)
  - 環境変数の読み込み機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
  - 自動 `.env` ロード順序: OS環境変数 > `.env.local` > `.env`。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - `.env` パーサーは `export KEY=val`、クォートやエスケープ、インラインコメントなどに対応。
  - 環境変数保護機能（既存 OS 環境変数を保護する `protected` セット）を実装。
  - Settings クラスを追加し、主要設定をプロパティ経由で取得:
    - J-Quants、kabu API、Slack トークン/チャンネル、DB パス（DuckDB, SQLite）、実行環境（development/paper_trading/live）、ログレベルなど。
  - 設定値のバリデーション（`KABUSYS_ENV` と `LOG_LEVEL` の有効値チェック）と必須変数未設定時の明確なエラーを提供。

- AI モジュール
  - ニュース NLP (`kabusys.ai.news_nlp`)
    - raw_news と news_symbols を使い、銘柄ごとのニュースを集約して OpenAI (gpt-4o-mini) によりセンチメントスコアを算出。
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST）を実装（UTC naive datetime で DB と比較）。
    - バッチング（最大 20 銘柄 / API コール）、トークン肥大対策（記事数上限・文字数トリム）を実装。
    - API 呼び出しは JSON Mode を利用、レスポンス検証（構造・型・既知コード・数値検証）を実装。
    - レート制限・ネットワーク断・タイムアウト・5xx を対象とした指数バックオフリトライを実装。
    - フェイルセーフ設計: API 失敗やパースエラーはスキップして継続、致命例外を抑制。
    - テスト容易性のため `_call_openai_api` を patch して差し替え可能。
    - 成果は `ai_scores` テーブルへ書き込み（部分失敗時に既存スコアを保護するため code を絞って DELETE → INSERT）。

  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily からの MA200 計算はルックアヘッドバイアスを避ける実装（target_date 未満のみ使用）。
    - マクロニュースは `news_nlp.calc_news_window` とキーワードフィルタで抽出し、OpenAI に投げて JSON をパース。
    - API 障害時は macro_sentiment=0.0 としてフェイルセーフ継続。
    - 計算結果は `market_regime` テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書込失敗時はロールバック処理あり。
    - テスト用に `_call_openai_api` を差し替え可能。

- データプラットフォーム (`kabusys.data`)
  - カレンダー管理 (`calendar_management`)
    - JPX カレンダーの管理、営業日判定機能を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - market_calendar が未取得の場合は曜日ベースのフォールバック（平日を営業日扱い）を実装。
    - 最大探索日数や健全性チェック、バックフィル方針（直近 _BACKFILL_DAYS 日を再取得）を実装。
    - 夜間バッチ `calendar_update_job` により J-Quants から差分取得して保存するフローを実装（fetch/save 関数は jquants_client に委譲、例外ハンドリングあり）。

  - ETL パイプライン (`pipeline`, `etl` 再エクスポート)
    - ETL のインターフェースと `ETLResult` データクラスを提供。ETL の取得数・保存数、品質チェック結果、エラーを集約。
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）を行う設計方針を採用。
    - 内部ユーティリティ（テーブル存在チェック、最大日付取得等）を実装。

- Research（研究用）モジュール (`kabusys.research`)
  - ファクター計算 (`factor_research`)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）、Value（PER, ROE）を計算する関数を実装。
    - DuckDB を用いた SQL ベースの計算により、price/financials のみ参照。出力は (date, code) ベースの辞書リスト。
    - データ不足時の None ハンドリング、ログ出力を実装。

  - 特徴量探索 (`feature_exploration`)
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21] 営業日）、IC（Spearman の ρ）計算、ランキング（同順位は平均ランク）、ファクター統計サマリーを実装。
    - pandas 等に依存せず標準ライブラリと DuckDB で実装。
    - rank 関数は浮動小数の丸め（round(v,12)）を用いて ties を適切に処理。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーはデフォルトで環境変数 `OPENAI_API_KEY` を参照。関数は引数 `api_key` で注入可能（テストやキー管理に配慮）。
- 自動 .env ロードは環境変数で無効化可能（`KABUSYS_DISABLE_AUTO_ENV_LOAD`）。

### Notes / 実装上の注意点
- すべての日付処理はルックアヘッドバイアスを避ける方針で実装（関数は内部で date.today()/datetime.today() を参照しない設計を意識）。
- DuckDB のバージョン差異対策（executemany の空リスト制約やリスト型バインドの挙動）に配慮した実装が各所にあります。
- OpenAI 呼び出しの共通化は行っているが、テスト検証のためモジュール内で `_call_openai_api` をローカルに持ち、外部モジュールとプライベート実装を共有しない設計になっています。
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY など。未設定時は Settings のプロパティアクセスで明確な ValueError を投げる。

---

今後のリリースで記録すべき主な候補
- strategy / execution / monitoring の実装状況に応じた機能追加。
- テストカバレッジ、CI/CD の追加とテスト用フックの拡充。
- デプロイ・運用に関するドキュメント（シークレット管理、バックテストワークフローなど）。
- jquants_client / kabu API クライアントのエラー・レート制御の改善。