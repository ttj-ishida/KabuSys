# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 初回リリース
最初の公開リリース。パッケージ全体の基盤機能、ETL / データ管理、リサーチ用ファクター、AI ベースのニュースセンチメント／市場レジーム判定などを実装。

### 追加 (Added)
- パッケージ基礎
  - `kabusys` パッケージ初期化、バージョン `0.1.0` を設定。
  - モジュールの公開 API（`data`, `strategy`, `execution`, `monitoring`）を __all__ に定義。

- 環境設定 / コンフィグ (`kabusys.config`)
  - .env ファイル自動ロード機構を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - `.env` / `.env.local` の読み込み順と上書きルールを実装（OS 環境変数を保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプションを実装。
  - .env パース機能を強化（コメント、export 構文、シングル/ダブルクォート、バックスラッシュエスケープ等に対応）。
  - 必須環境変数取得ヘルパー `_require` と `Settings` クラスを実装:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須設定をプロパティで提供。
    - データベースパス (DUCKDB_PATH, SQLITE_PATH)、監視設定（PIDファイル・閾値）、環境 (KABUSYS_ENV)、ログレベル (LOG_LEVEL) などの既定値・検証を実装。
    - 環境値の検証（KABUSYS_ENV と LOG_LEVEL の有効値チェック）。

- AI: ニュース NLP (`kabusys.ai.news_nlp`)
  - raw_news と news_symbols を基に、銘柄毎にニュースを集約し OpenAI（gpt-4o-mini, JSON mode）でセンチメントを算出して `ai_scores` テーブルに書き込む処理を実装。
  - ニュース収集ウィンドウ計算（JST ベース → UTC 変換）を実装（前日 15:00 JST 〜 当日 08:30 JST）。
  - バッチ処理（最大 20 銘柄／API 呼び出し）および 1 銘柄あたりの最大記事数/文字数制限を実装（トークン肥大化対策）。
  - OpenAI 呼び出しに対するリトライ（429・ネットワーク断・タイムアウト・5xx を対象）と指数バックオフを実装。
  - レスポンスのバリデーションとパース耐性（JSON 抜き出し、型検査、未知コード無視、スコア数値変換、±1.0 のクリッピング）。
  - 部分書込みを考慮した冪等的 DB 更新ロジック（対象コードのみ DELETE → INSERT）。
  - テスト容易性のため OpenAI 呼び出しラッパーをモック差し替え可能に実装。

- AI: 市場レジーム判定 (`kabusys.ai.regime_detector`)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
  - prices_daily からの MA200 比率計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）とデータ不足時のフォールバック。
  - raw_news からマクロキーワードで記事タイトルを抽出し、OpenAI（gpt-4o-mini, JSON mode）でマクロセンチメントを算出。
  - API 障害時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
  - レジームスコア合成とラベル判定閾値（bull/bear/neutral 設定）。
  - 冪等的な market_regime テーブルへの書き込み（BEGIN / DELETE / INSERT / COMMIT, 失敗時は ROLLBACK）。

- データプラットフォーム / ETL (`kabusys.data.pipeline`, `kabusys.data.etl`)
  - ETL パイプラインの結果を表す `ETLResult` データクラスを実装（取得件数、保存件数、品質問題、エラー等を表現）。
  - 差分更新、バックフィル日数、品質チェックの設計方針をコードに反映（jquants_client を用いた差分取得と冪等保存を想定）。
  - DuckDB のテーブル存在チェック、最大日付取得等のユーティリティを実装（ETL 処理基盤）。

- カレンダー管理 (`kabusys.data.calendar_management`)
  - market_calendar を用いた営業日判定・探索ロジックを実装:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB 登録値優先、未登録日は曜日ベースのフォールバックを実装し一貫性を保持。
    - 探索上限 (_MAX_SEARCH_DAYS) による無限ループ防御、先読み／バックフィル、健全性チェックを実装。
  - calendar_update_job を実装し J-Quants API からの差分取得と market_calendar の冪等保存を実施。

- リサーチ / ファクター計算 (`kabusys.research`)
  - ファクター計算モジュールを実装:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - calc_volatility: 20 日 ATR（平均）、相対 ATR、平均売買代金、出来高比率。
    - calc_value: PER、ROE（raw_financials から target_date 以前の最新データを使用）。
  - 特徴量探索モジュールを実装:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン算出（LEAD を利用）。
    - calc_ic: スピアマンランク相関（IC）計算。データ不足時は None を返す。
    - rank: 同順位は平均ランク化するランク変換実装（小数丸めで ties を安定処理）。
    - factor_summary: 各ファクターの count/mean/std/min/max/median を標準ライブラリのみで算出。
  - いずれのリサーチ関数も DuckDB 接続のみ参照し、外部ネットワークアクセスや発注 API へはアクセスしない設計（安全・検証容易）。

- テスト性・運用性
  - OpenAI 呼び出し部分に対してモック差し替え可能な設計を採用（ユニットテスト容易化）。
  - ルックアヘッドバイアス防止のため、各関数で datetime.today() / date.today() などの直接参照を避け引数で日付を受け取る設計。
  - ロギングを適切に追加し、異常時は警告/例外を記録するように実装。

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 変更 (Changed)
- （初回リリースのため該当なし）

### 廃止 (Deprecated)
- （初回リリースのため該当なし）

---

注:
- 実装はコードベースからの推測に基づき CHANGELOG を作成しています。実際のリリースノート作成時は変更履歴・コミットログ・リリース担当者の記載と照合してください。