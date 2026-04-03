# CHANGELOG

すべての主な変更点は Keep a Changelog の形式で記録しています。  
初版リリース: 0.1.0

## [Unreleased]
- なし

## [0.1.0] - 2026-04-03
初回公開リリース。日本株自動売買フレームワークの基礎機能を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージの基本エントリポイントを追加（src/kabusys/__init__.py）。
  - バージョン情報を `__version__ = "0.1.0"` として管理。

- 環境設定・ロード機能（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml を基準）により CWD 非依存で動作。
  - .env と .env.local の優先度を実装（OS 環境変数は保護）。自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。
  - .env の行パースは export プレフィックス、クォート（シングル・ダブル）、バックスラッシュエスケープ、インラインコメントを考慮して堅牢に実装。
  - 設定取得用 `Settings` クラスを提供。J-Quants、kabu API、LINE、データベースパス、監視閾値、実行環境 / ログレベルの妥当性チェックを実装（不正値で ValueError）。
  - 環境判定ユーティリティ (is_live / is_paper / is_dev) を提供。

- AI 関連（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（JST → UTC への変換）、1 銘柄あたりの記事数・文字数トリム、チャンク（最大 20 銘柄）処理、JSON Mode を利用したレスポンス検証を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、レスポンスのバリデーション（構造・型・既知コード・数値チェック）、スコアの ±1.0 クリップを実装。
    - 部分失敗時の既存スコア保護（該当コードのみ DELETE → INSERT）を考慮した冪等的 DB 書き込み。
    - 公開関数: score_news(conn, target_date, api_key=None)、calc_news_window(...) 等。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・保存する処理を実装。
    - prices_daily からのデータ取得はルックアヘッドの排除（target_date 未満のみ）を徹底。
    - マクロニュース抽出、OpenAI（gpt-4o-mini）呼び出し、リトライ/フォールバック（API 失敗時は macro_sentiment=0.0）ロジックを実装。
    - DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - 公開関数: score_regime(conn, target_date, api_key=None)。

  - ai パッケージのエクスポート（src/kabusys/ai/__init__.py）
    - score_news をトップレベルから利用可能に。

- リサーチ／ファクター計算（src/kabusys/research）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算する calc_momentum(conn, target_date) を実装。データ不足時の扱い（None）を定義。
    - Volatility / Liquidity: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算する calc_volatility(conn, target_date) を実装。真のレンジ計算（true_range）は high/low/prev_close の NULL を適切に扱う。
    - Value: raw_financials から最新財務を取得して PER / ROE を計算する calc_value(conn, target_date) を実装。
    - DuckDB を用いた SQL ベースの実装で、結果は (date, code) を含む dict のリストで返却。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 calc_forward_returns(conn, target_date, horizons=None) を実装（デフォルト horizons=[1,5,21]）。ホライズンは検証済みの範囲チェックを行う。
    - Information Coefficient（Spearman ρ）計算 calc_ic(...): ランクの取り方・欠損処理・最小サンプルチェックを実装。
    - ランク変換ユーティリティ rank(values)（同順位は平均ランクの処理、丸め誤差対策を含む）。
    - 統計サマリー factor_summary(records, columns)（count/mean/std/min/max/median）を実装。
  - research パッケージのエクスポート（src/kabusys/research/__init__.py）
    - 主要な関数をトップレベルに公開（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- データプラットフォーム関連（src/kabusys/data）
  - 市場カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーを扱うユーティリティを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar テーブルがない場合の曜日ベースフォールバック、DB がまばらな場合の一貫した補完ロジック、最大探索日数制限を実装。
    - calendar_update_job(conn, lookahead_days=...) により J-Quants から差分取得して冪等的に保存する仕組みを実装（バックフィル・健全性チェック付き）。
  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult データクラスを実装して ETL の集計結果・品質問題・エラーを構造化して返却。
    - 差分取得、バックフィル、保存（jquants_client の save_* を想定）、品質チェック（quality モジュール連携）を行う設計を反映。
    - etl モジュールで ETLResult を再エクスポート。
  - データユーティリティ（src/kabusys/data/__init__.py）はパッケージの土台を提供（空の __init__）。

- その他外部連携想定
  - OpenAI（環境変数 OPENAI_API_KEY または引数で注入）を利用する AI 処理を複数実装。
  - J-Quants クライアント（kabusys.data.jquants_client）および kabu ステーション API（設定）を想定した設定項目を実装。
  - LINE Messaging API 用の設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を設定で保持。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

---

開発者向け補足（実装上の重要事項）
- 時系列処理ではルックアヘッドバイアス防止を徹底（datetime.today()/date.today() を処理内で参照しない設計、target_date に基づく計算）。
- DB 書き込みは可能な限り冪等に設計（DELETE → INSERT など）。
- OpenAI API 呼び出しは JSON Mode を前提に厳密なバリデーションを実施し、API エラー時はフェイルセーフ（スコア 0.0 やスキップ）で継続する方針。
- DuckDB のバージョン互換性（executemany の挙動など）を考慮した実装上の注意あり。

今後の予定（例）
- ai スコアのモデル・プロンプトチューニング、エンドツーエンドの戦略実行連携（strategy / execution / monitoring モジュール）およびユニットテスト/CI の充実。