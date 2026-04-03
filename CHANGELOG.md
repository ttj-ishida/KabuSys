# CHANGELOG

すべての重要な変更点をこのファイルに記録します。  
このプロジェクトでは Keep a Changelog の形式に準拠し、セマンティックバージョニングを採用します。

※本 CHANGELOG は付属のソースコード（src/kabusys 以下）から機能・設計意図を推測して作成しています。

## [0.1.0] - 2026-04-03

初期リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加点・設計方針は以下の通りです。

### Added
- パッケージ基本情報
  - パッケージ名・バージョン管理（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ で定義。

- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイル自動ロード（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env の行パーサ実装（コメント/クォート/エスケープ対応）。
  - Settings クラスでアプリケーション設定をプロパティとして公開（J-Quants、kabuステーション、LINE、DBパス、監視閾値、env/log_level 判定等）。
  - 必須環境変数取得ヘルパー（_require）で未設定時に明確なエラーを返す。

- AI モジュール（src/kabusys/ai）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode でバッチ評価。
    - チャンクバッチ (最大 20 銘柄) / 1銘柄あたりの記事数・文字数制限（過大入力対策）。
    - 再試行（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフ。
    - レスポンス検証ロジック（JSON 抽出、results 配列の検証、未知コード無視、数値検証、±1.0 でクリップ）。
    - DuckDB への冪等書き込み（取得済みコードの DELETE → INSERT、executemany 空リスト回避）。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
    - タイムウィンドウ計算ユーティリティ calc_news_window(target_date)（JSTベースで前日15:00～当日08:30 を UTC に変換）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を判定。
    - マクロニュース抽出（マクロキーワードによるタイトルフィルタ、最大 20 件）。
    - OpenAI 呼び出しを独立実装（モジュール間の結合を避ける）。
    - API エラー時はフェイルセーフとして macro_sentiment = 0.0 を使用。
    - DuckDB の market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時に 1 を返す。

  - ai パッケージの __all__ に score_news を公開。

- データモジュール（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日判定 API を提供。
    - market_calendar テーブルの存在チェック、DB 優先・未登録日は曜日ベースでフォールバックする一貫したロジック。
    - next/prev_trading_day は探索上限を設定して無限ループを防止（_MAX_SEARCH_DAYS）。
    - calendar_update_job(conn, lookahead_days=90) により J-Quants API からの差分フェッチ → 冪等保存（J-Quants クライアント呼び出し経由）。
    - バックフィル / 健全性チェック / ロギングを実装。

  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult データクラスを定義（取得件数、保存件数、品質問題、エラー一覧等を保持）。
    - 差分更新・バックフィル・品質チェック設計（jquants_client / quality モジュールと連携する想定）。
    - DuckDB テーブル存在確認、最大日付取得等の内部ユーティリティ。
    - src/kabusys/data/etl.py で ETLResult を再エクスポート。

- 研究（research）パッケージ（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム: mom_1m/mom_3m/mom_6m、ma200_dev（200日MA乖離）を計算する calc_momentum。
    - ボラティリティ/流動性: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算する calc_volatility。
    - バリュー: 最新の raw_financials と価格を結合して PER/ROE を計算する calc_value。
    - DuckDB に対する SQL ベース実装、データ不足時の None 戻し、結果は (date, code) をキーとする dict リストで返す。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 calc_forward_returns（任意のホライズンリストに対応、入力検証あり）。
    - Information Coefficient（Spearman の ρ）を計算する calc_ic（結合・欠損除外・最小サンプルチェック）。
    - ランク変換ユーティリティ rank（同順位は平均ランクで処理、丸め対策あり）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median を計算）。

- 複数モジュールでの共通設計方針
  - ルックアヘッドバイアス防止のため、datetime.today() / date.today() の直接参照を避け、呼び出し側から target_date を受け取る設計。
  - OpenAI 呼び出し周りは再試行・バックオフ・エラーハンドリングを厳格に実装し、API エラー時はフェイルセーフ（スコア 0.0 やスキップ）で継続する設計。
  - DuckDB の互換性（executemany への空リスト不可など）を考慮した実装。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Security
- OpenAI API キーは引数経由で注入可能（api_key 引数）かつ環境変数 OPENAI_API_KEY を利用。未設定時は明示的に ValueError を投げることで誤設定を検出しやすくしています。

---

開発ノート / 注意点
- 自動 .env ロードはプロジェクトルート検出に依存するため、パッケージ配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数で設定して自動ロードを無効化できます。
- OpenAI 呼び出し箇所はユニットテスト容易性のため関数をパッチして差し替え可能（_call_openai_api を patch）。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials, market_regime など）が前提です。実行時は対応するテーブルが存在することを確認してください。

今後の予定（例）
- strategy / execution / monitoring モジュールの具現化（現状はパッケージ名としてプレースホルダ）。
- ai モジュールの拡張（より多様なプロンプト・モデル対応、ロギング強化）。
- ETL の運用周り（スケジューリング、監査ログ、通知連携）の実装。

--- 

（この CHANGELOG はソースコードの実装内容とドキュメント文字列から生成した推測に基づくため、実際のリリースノート作成時はリリース担当者が内容をレビュー・補正してください。）