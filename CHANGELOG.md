# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載します。  
このファイルはコードベース（src/kabusys 以下）から推測して作成した初期リリース向けの変更履歴です。

## [0.1.0] - 2026-03-29
初期リリース。日本株自動売買システムのコアライブラリを提供します。

### 追加 (Added)
- パッケージ基盤
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。
  - パッケージの公開 API に data / strategy / execution / monitoring を含める（`__all__`）。

- 環境設定（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml）を実装。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env/.env.local の読み込み順序と上書きポリシー（OS 環境変数は保護）を実装。
  - .env パーサーは `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応。
  - 必須設定取得時に未設定で例外を投げる `_require`、設定値の検証（KABUSYS_ENV、LOG_LEVEL）の実装。
  - Settings による公開プロパティ:
    - J-Quants / kabu API / Slack / DB パス（duckdb/sqlite）/ 環境種別判定メソッド（is_live/is_paper/is_dev）等。

- AI モジュール（kabusys.ai）
  - news_nlp モジュール
    - raw_news と news_symbols を用いて銘柄ごとのニューステキストを集約し、OpenAI（gpt-4o-mini、JSON Mode）でセンチメントスコアを取得して `ai_scores` テーブルへ書き込む `score_news` を実装。
    - タイムウィンドウの計算 (`calc_news_window`) は JST 基準（前日 15:00 ～ 当日 08:30）を UTC に変換して使用。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたりの最大記事数と文字数のトリム、JSON レスポンスの検証、スコア ±1.0 のクリップ。
    - レート制限/ネットワーク/タイムアウト/5xx に対する指数バックオフのリトライ、失敗時はログ出力してスキップするフェイルセーフ動作。
    - テスト容易性のため OpenAI 呼び出し箇所をモック差し替え可能（`_call_openai_api` を patch 可能）。
  - regime_detector モジュール
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（`bull`/`neutral`/`bear`）を判定する `score_regime` を実装。
    - prices_daily から ma200_ratio を計算、raw_news からマクロキーワードでフィルタしたタイトルを抽出、OpenAI（gpt-4o-mini）でマクロセンチメント評価、スコア合成後 `market_regime` テーブルへ冪等書き込み。
    - API エラー時はマクロスコアを 0.0 にフォールバックする安全策、再試行ロジック（リトライ回数・指数バックオフ）を実装。

- データ処理（kabusys.data）
  - calendar_management
    - JPX カレンダー（market_calendar）に基づく営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。DB にデータがない場合は土日ベースのフォールバック。
    - 夜間バッチ更新ジョブ `calendar_update_job` を実装（J-Quants クライアント経由で差分取得、バックフィル、サニティチェック、冪等保存）。
  - pipeline / etl
    - ETL 結果を格納するデータクラス `ETLResult` を実装（取得件数・保存件数・品質課題・エラー等を格納、has_errors/has_quality_errors/properties、to_dict メソッドを提供）。
    - ETL パイプラインユーティリティ（差分取得、バックフィル、保存、品質チェックの設計方針とユーティリティ関数）を実装。
    - `data.etl` から `ETLResult` を再エクスポート。

- リサーチ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M）、200日移動平均乖離、ATR（20日）、平均出来高/売買代金などのファクター計算関数を実装（`calc_momentum`、`calc_volatility`、`calc_value`）。
    - DuckDB 上で SQL ウィンドウ関数を用いて効率的に計算。データ不足時の None ハンドリング。
  - feature_exploration
    - 将来リターン計算 `calc_forward_returns`（horizons の汎用対応）、スピアマンランク相関による IC 計算 `calc_ic`、ランク変換ユーティリティ `rank`、統計サマリー `factor_summary` を実装。
    - pandas 等に依存しない純標準ライブラリ実装。

### 変更 (Changed)
- なし（初期リリースのため既存からの変更はなし）。将来的に API や DB スキーマの安定化に伴い変更を明記予定。

### 修正 (Fixed)
- なし（初期リリース）。

### 既知の注意点 / 設計上の決定
- ルックアヘッドバイアス防止:
  - AI スコアリング・レジーム判定・ファクター計算等の関数は内部で datetime.today()/date.today() を直接参照しない設計（呼び出し側から `target_date` を渡す）。
  - DB クエリでは排他条件（例えば date < target_date）や半開区間を徹底して使用。
- OpenAI 呼び出し:
  - モデルは gpt-4o-mini を想定、JSON Mode（response_format）を使用して厳密な JSON を期待する。
  - API レスポンスのパース/バリデーションに失敗した場合は例外を上位に投げず、該当チャンク/スコアをスキップする（フェイルセーフ）。
- 環境変数の自動ロード:
  - OS 側環境変数は上書き保護される（.env/.env.local の override ポリシー）。
  - テストや CI のために自動ロードを抑止するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。
- DB 書き込みは冪等性を重視:
  - market_regime / ai_scores 等は既存レコードの削除 → 挿入、BEGIN/COMMIT/ROLLBACK を用いたトランザクション制御。

### 推奨事項（運用上）
- 環境変数:
  - 必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等）を .env または環境で設定すること。
  - `KABUSYS_ENV` は development / paper_trading / live のいずれかを設定。`LOG_LEVEL` は標準的なログレベルを使用。
- テスト:
  - OpenAI の外部呼び出し部分は内部関数を patch して差し替えられる設計のため、ユニットテストではモック化を推奨。

---

今後のリリースでは、以下のような項目を CHANGELOG に追加予定です:
- DB スキーマ変更（テーブル追加/カラム変更）
- Strategy / Execution / Monitoring サブパッケージの実装状況と API 変更
- 性能改善（クエリ最適化、バッチ戦略）
- セキュリティ修正や外部 API 互換性に関する変更

（注）本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のリリースノートはリポジトリのコミット履歴やリリース管理情報に基づいて作成してください。