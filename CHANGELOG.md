# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトではセマンティックバージョニングを採用しています。

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-03-29

初回リリース — 日本株自動売買システムの基盤機能を実装しました。主な追加点・設計方針は以下の通りです。

### 追加 (Added)
- パッケージ基本情報
  - パッケージ初期化: kabusys.__version__ = "0.1.0" を定義。
  - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ に公開。

- 設定管理
  - kabusys.config: 環境変数・設定管理モジュールを実装。
    - .env / .env.local の自動ロード（プロジェクトルート判定: .git または pyproject.toml を探索）。
    - OS 環境変数を保護する protected オプション。
    - export KEY=val / クォート・エスケープ・インラインコメント対応の .env パーサ実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - Settings クラスで主要設定をプロパティとして公開（J-Quants, kabu API, Slack, DBパス, env/log_level 判定など）。
    - env / log_level の値検証（許容値検査）。
    - 必須環境変数未設定時に ValueError を送出する _require 関数。

- データ関連
  - kabusys.data.pipeline
    - ETLResult データクラスを公開（ETL 実行結果の構造化）。
    - 差分更新、バックフィル、品質チェックのための基礎ロジック（定数・ヘルパ関数）。
    - DuckDB を想定した最大日付取得、テーブル存在チェック等のユーティリティ。
  - kabusys.data.etl
    - pipeline.ETLResult を公開インターフェースとして再エクスポート。
  - kabusys.data.calendar_management
    - JPX カレンダー管理（market_calendar 用の読み書き・判定ロジック）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日ユーティリティ。
    - calendar_update_job: J-Quants からの差分取得と冪等保存（バックフィル、健全性チェックを含む）。
    - DB が未取得のときは曜日ベースのフォールバックを採用。

- リサーチ（ファクター計算・特徴量探索）
  - kabusys.research.factor_research
    - calc_momentum: 1M/3M/6M リターンおよび 200 日 MA 乖離(ma200_dev) の計算。
    - calc_volatility: 20 日 ATR, 相対ATR(atr_pct), 20 日平均売買代金, 出来高比(volume_ratio) の計算。
    - calc_value: raw_financials からの EPS/ROE を組み合わせた PER/ROE の計算。
    - DuckDB クエリベースで営業日を意識した窓計算を実装。
  - kabusys.research.feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算（LEAD を使用）。
    - calc_ic: スピアマン（ランク）相関による IC 計算（結合・欠損除外・最小レコードチェック）。
    - rank: 同順位は平均ランクで処理するランク付け実装（丸め誤差対策あり）。
    - factor_summary: count/mean/std/min/max/median を返す統計サマリー実装。
    - 研究系 API を __all__ で公開（zscore_normalize は data.stats から再利用）。

- AI（ニュース NLP / レジーム検出）
  - kabusys.ai.news_nlp
    - score_news: raw_news と news_symbols を元に銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込み。
    - タイムウィンドウ定義（JST: 前日15:00 ～ 当日08:30 を UTC に変換して扱う）。
    - 1銘柄あたりの記事数と文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）で OpenAI（gpt-4o-mini, JSON mode）へ送信。
    - レート制限・ネットワークエラー・タイムアウト・5xx に対する指数バックオフリトライ。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score 検証、スコアクリップ）。
    - 部分成功に対応した冪等的 DB 更新（DELETE してから INSERT、失敗時はロールバック）。
    - テスト用フック: _call_openai_api の patch による差し替えが可能。
  - kabusys.ai.regime_detector
    - score_regime: ETF 1321（Nikkei 225 連動）の 200 日 MA 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出して market_regime テーブルに保存。
    - calc_ma200_ratio: target_date 未満のデータのみ使用してルックアヘッドを回避。
    - マクロニュースは news_nlp.calc_news_window と raw_news を用いて取得。
    - OpenAI 呼び出しは独立実装でモジュール結合を防止。
    - API 障害時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - 冪等的 DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理。

### 変更 (Changed)
- （初回リリースのため、過去バージョンとの差分はありません）

### 修正 (Fixed)
- （初回リリースのため、修正履歴はありません）

### 既知の注意点 (Notes / Known issues)
- 外部依存:
  - OpenAI SDK（OpenAI クライアント）および duckdb に依存します。これらが環境に存在する必要があります。
- タイムゾーン:
  - news_nlp・regime_detector の窓計算は UTC naïve の datetime を使用しています（JST と厳密に対応させるために変換を明示的に実装済み）。タイムゾーン混入を避ける設計です。
- フェイルセーフ:
  - LLM 呼び出しの失敗はフェイルセーフにより中立（0.0）にフォールバックし、ETL・スコア処理は継続する方針です。
- テスト性:
  - OpenAI 呼び出し部分はモック差し替え可能な設計。単体テストで外部 API を呼ばないようにできます。
- 未実装/プレースホルダ:
  - パッケージ __all__ に含まれる strategy, execution, monitoring モジュールは外部から参照される可能性がありますが、ここで示されるのは現フェーズでの公開シンボルです（実装の有無はコードベース次第）。

### 破壊的変更 (Breaking Changes)
- なし（初回リリース）

---

リリースに含まれる主要な設計方針
- ルックアヘッドバイアス回避: date.today() / datetime.today() を直接参照せず、target_date を明示的に渡す設計。
- DB 操作は可能な限り冪等化（DELETE→INSERT、ON CONFLICT、executemany の空リスト回避）して、部分失敗時にも既存データを保護。
- API 呼び出しはリトライ・バックオフ・非致命的フォールバックを採用して、バッチ処理の堅牢性を高める。

（この CHANGELOG はコードを参照して推測に基づき作成しています。実際のリリースノート作成時には追加の運用情報・実行手順・依存関係・セキュリティ注意事項を追記してください。）