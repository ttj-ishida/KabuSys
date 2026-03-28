# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-28
初回公開リリース。以下の主要機能とモジュールを追加しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__init__、バージョン `0.1.0`）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ にてエクスポート。

- 設定管理
  - kabusys.config モジュールを追加。
    - .env ファイル（.env, .env.local）と OS 環境変数から設定を読み込む自動読み込み機能を実装（プロジェクトルートは .git / pyproject.toml から検出）。
    - .env のパースは export KEY=val やクォート、エスケープ、インラインコメントに対応。
    - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - 必須環境変数取得のヘルパー `_require` と Settings クラスを提供。
    - J-Quants / kabuステーション / Slack / DB パス / 環境フラグ（development/paper_trading/live）/ログレベルの設定をマッピング。

- データプラットフォーム (data)
  - ETL パイプライン（kabusys.data.pipeline）を実装。
    - 差分取得、保存（idempotent）、品質チェックを行う設計。ETL の結果を表す dataclass `ETLResult` を公開。
    - DuckDB を用いた最大日付取得やテーブル存在チェックなどのユーティリティを含む。
    - デフォルトのバックフィル、カレンダー先読みなどの設定を備える。
  - calendar_management モジュールを追加。
    - JPX マーケットカレンダー管理（market_calendar テーブル）と夜間更新ジョブ `calendar_update_job` を実装。
    - 営業日判定・前後営業日取得のユーティリティ（is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day）を提供。
    - DB にカレンダーがない・一部しかない場合の曜日ベースのフォールバックをサポート。
    - 最大探索日数や健全性チェック、バックフィル挙動を実装。
  - jquants_client（参照）と連携する前提で設計。

- リサーチ (research)
  - ファクター計算モジュールを追加（kabusys.research.factor_research）。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（PBR などは未実装）。
    - DuckDB SQL + Python で完結する設計。データ不足時は None を返す。
  - 特徴量探索モジュールを追加（kabusys.research.feature_exploration）。
    - calc_forward_returns: 与えられた horizon（営業日）での将来リターン取得（デフォルト [1,5,21]）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算。
    - rank: 同順位の平均ランク処理を行うユーティリティ（丸めによる ties 対応）。
    - factor_summary: 各ファクターカラムの count/mean/std/min/max/median を算出。
  - research パッケージは zscore_normalize（kabusys.data.stats 由来）などを再エクスポート。

- AI（LLM）連携
  - ニュース NLP（kabusys.ai.news_nlp）を追加。
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを生成し、OpenAI の Chat Completions（gpt-4o-mini）を用いて銘柄ごとのセンチメントを -1.0〜1.0 のスコアで評価。
    - API 呼び出しはバッチ処理（最大 20 銘柄/チャンク）、トークン肥大化対策（記事数/文字数上限）を実装。
    - 429、ネットワーク断、タイムアウト、5xx に対する指数バックオフでのリトライを実装。その他エラー時はフェイルセーフでスキップし続行。
    - レスポンスのバリデーションとスコアのクリップ、部分成功時の idempotent な DB 書き換え（DELETE → INSERT）処理を実装。
    - ユニットテストのために内部の _call_openai_api をパッチで差し替え可能。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。
    - ニュースウィンドウ（JST 前日 15:00 ～ 当日 08:30）を UTC naive datetime で計算する calc_news_window を提供。
  - 市場レジーム判定（kabusys.ai.regime_detector）を追加。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等で保存。
    - マクロニュース抽出のためのキーワードリストを内包し、最大記事数やモデル名、リトライ挙動などを定義。
    - API Key 解決、ma200 比率計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）、LLM 呼び出し、スコア合成、DB へのトランザクション書き込みを実装。
    - API 呼び出し失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフを採用。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- 設計方針・堅牢性
  - 全ての AI / リサーチ処理でルックアヘッドバイアスを避けるため、datetime.today()/date.today() を直接参照せず、target_date ベースで計算する設計。
  - DuckDB に対する executemany の仕様差異（空リスト不可）を考慮した実装。
  - DB 書き込みは冪等性を重視（DELETE → INSERT、トランザクション BEGIN/COMMIT/ROLLBACK）し、部分失敗時に既存データを過剰に消さない工夫。
  - ロギングを広範に導入し、失敗時には WARN/INFO/EXCEPTION で状況を記録。
  - OpenAI SDK のエラー型や将来の変化に配慮した防御的な例外処理（status_code の有無を getattr で安全に扱う等）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 既知の制約 / 注意点
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY によって解決される。未設定の場合は ValueError を送出する箇所があるため運用時に設定が必要。
- news_nlp と regime_detector は実際の OpenAI 呼び出しを行うため、テスト時は提供されたパッチポイントを使ってモックすることを推奨。
- 一部の機能は jquants_client 等の外部依存に基づく（本実装では参照）。実運用には API クライアントの設定が必要。

---

作成: kabusys v0.1.0 リリースノート（自動生成）