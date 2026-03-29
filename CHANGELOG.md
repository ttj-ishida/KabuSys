# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog のフォーマットに従っています。  

※日付はリリース日を示します。リリース前の項目は Unreleased に記載してください。

## [Unreleased]

（現状、次回リリースに向けた未リリースの変更はありません）

---

## [0.1.0] - 2026-03-29

初回公開リリース。日本株自動売買プラットフォーム「KabuSys」のコアライブラリを実装・公開。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開 API を __all__ で整理（data, strategy, execution, monitoring）。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索）。
  - POSIX 風の .env 行パーサを実装（export プレフィックス、クォート/エスケープ、行内コメント処理対応）。
  - .env / .env.local の読み込み優先度を実装（OS 環境変数を保護する protected 機能）。
  - Settings クラスを提供し、必須環境変数取得メソッド（_require）を定義。
  - 設定項目: J-Quants / kabu API / Slack / データベースパス（DuckDB/SQLite）/実行環境（development/paper_trading/live）/ログレベル等をサポート。値検証（有効な env・ログレベル）を実装。
  - 開発に配慮したデフォルト値・保護機能を用意。

- AI/NLP（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとのニュースを構成。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive で計算）。
    - OpenAI（gpt-4o-mini, JSON Mode）で銘柄ごとのセンチメントをバッチ処理。1 API コールあたり最大 20 銘柄。
    - トークン肥大化対策: 1 銘柄あたり最大記事数（10）・最大文字数（3000）でトリム。
    - エクスポネンシャルバックオフによるリトライ（RateLimit/ネットワーク/5xx/タイムアウトに対応）。
    - レスポンス検証ロジックを実装（JSON 抽出、results 配列、code と score の検証、スコアを ±1.0 にクリップ）。
    - スコアを ai_scores テーブルへ冪等的に書き込み（該当コードの DELETE → INSERT）。DuckDB の executemany 空パラメータ制約に配慮。
    - テスト容易性: _call_openai_api を patch 可能に設計。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせてレジーム（bull / neutral / bear）を日次判定。
    - prices_daily から ma200_ratio を算出（target_date 未満のデータのみ使用してルックアヘッドを防止）。
    - raw_news からマクロキーワードでフィルタした記事タイトルを抽出し LLM により macro_sentiment を取得（記事なしの場合は LLM 呼び出しを行わず 0.0）。
    - OpenAI 呼び出しは再試行・エラーハンドリングを備え、失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - レジームスコア合成後、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 設計上、datetime.today()/date.today() を直接参照せず、外部から target_date を与えることでルックアヘッドバイアスを防止。

- データ管理（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar）を前提とした営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB にカレンダー情報がない場合の曜日ベースフォールバック（週末は休場）を実装し、DB 登録値を優先する一貫した挙動を保証。
    - calendar_update_job を実装し、J-Quants API 経由で差分取得 → 保存（jq.fetch_market_calendar / jq.save_market_calendar を利用）を行う。バックフィル・健全性チェックを備える。
    - 最大探索日数などの保護（_MAX_SEARCH_DAYS, _SANITY_MAX_FUTURE_DAYS 等）を実装。

  - ETL / パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを実装（ETL 実行結果のサマリ、品質チェック情報、エラー一覧を保持）。
    - 差分更新・バックフィル・品質チェックの設計方針を反映したユーティリティを実装。
    - kabusys.data.etl で pipeline.ETLResult を再エクスポート。

- リサーチ / ファクター（kabusys.research）
  - factor_research
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER, ROE）、Volatility（20 日 ATR）など主要ファクターを DuckDB 参照で計算する関数を実装（calc_momentum, calc_value, calc_volatility）。
    - 入出力は (date, code) ベースの dict リスト。
    - データ不足時は None を返す等、堅牢性に配慮。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）に対応。
    - IC（Information Coefficient）計算（calc_ic）: スピアマン順位相関を実装（最小有効レコード数チェック）。
    - ランク変換ユーティリティ（rank）およびファクター統計サマリ（factor_summary）を実装。
  - 研究用ユーティリティは pandas 等外部依存無しで標準ライブラリ + DuckDB のみで動作。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーや各種シークレットは Settings で必須として明示。環境変数未設定時は明確に ValueError を送出して通知。

### 既知の注意点 / 設計上の決定
- OpenAI 呼び出しは外部 API であり、API キー・ネットワーク・レート制限に依存するため、失敗時はフェイルセーフ（スコア 0.0 や処理スキップ）で継続する設計です。重要な運用ではリトライ設定や監視を強化してください。
- .env パーサは多くのケースを扱いますが、特殊な .env 書式については想定外の動作をする可能性があります。
- DuckDB による executemany の空リスト挙動など互換性の課題に対してワークアラウンドを実装していますが、使用する DuckDB バージョンにより差異が出る場合があります。
- jquants_client（kabusys.data.jquants_client）や Slack/kabu API 呼び出し部分は本コード内で呼び出し点を想定していますが、実運用では適切な認証情報と API クライアントの実装が必要です。
- ルックアヘッドバイアス防止のため、すべての日付参照は外部から渡す target_date ベースで動作します（内部で date.today() を直接参照しない設計）。

---

開発・運用上の質問や追加のリリースノート要望があればお知らせください。