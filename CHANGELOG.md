# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog の仕様に準拠しています。  
[https://keepachangelog.com/ja/1.0.0/]

なお、本CHANGELOGはコードベースの実装内容から推測して作成しています。

## [0.1.0] - 2026-03-28

初回リリース — 日本株自動売買システム "KabuSys" の基盤機能を実装・公開。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 として定義。公開 API として data / strategy / execution / monitoring を __all__ に追加。

- 設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを実装。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサを実装（export 前置、クォート、エスケープ、行内コメント処理に対応）。
  - 環境変数読み出し用 Settings クラスを追加。J-Quants / kabuステーション / Slack / DB パス / 実行環境 (development/paper_trading/live) / ログレベル等をプロパティで取得し、未設定や不正値で適切に例外を投げる。
  - duckdb/sqlite のデフォルトパス（data/...）の expansion をサポート。

- ニュースNLP (kabusys.ai.news_nlp)
  - raw_news と news_symbols を元に、指定ウィンドウ（前日15:00 JST〜当日08:30 JST）内のニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON Mode を利用して銘柄別センチメント（-1.0〜1.0）を算出する機能を実装。
  - バッチ処理（最大20銘柄／APIコール）、トークン肥大化対策（記事数・文字数制限）、レスポンスバリデーション、スコアの ±1.0 クリップ、部分成功時の DB 置換（DELETE→INSERT）といった実用的な ETL 的配慮を導入。
  - リトライ戦略（429, ネットワーク断, タイムアウト, 5xx）を指数バックオフで実装。テスト時に API 呼び出しを差し替え可能な内部ラッパーを用意。
  - API 未設定時は ValueError を送出。

- 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321（国内日経225連動ETF）の 200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定し、market_regime テーブルに冪等的に保存する機能を実装。
  - マクロニュース抽出（キーワード群によるフィルタ）、OpenAI 呼び出し、リトライ・フェイルセーフ（API失敗時は macro_sentiment=0.0）を実装。
  - ルックアヘッドバイアス対策: date 引数ベースの処理、DB クエリは target_date 未満を利用する等の設計。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research モジュールにて以下のファクター計算を実装:
    - モメンタム: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離）
    - ボラティリティ・流動性: atr_20, atr_pct, avg_turnover, volume_ratio（20日ベース）
    - バリュー: PER, ROE（raw_financials と prices_daily を結合）
  - feature_exploration モジュールにて:
    - 将来リターン計算 calc_forward_returns（任意ホライズン、デフォルト [1,5,21]）
    - IC（Spearman ρ）計算 calc_ic（ランク相関）
    - ランク変換ユーティリティ rank（同順位は平均ランク）
    - ファクター統計サマリー factor_summary（count, mean, std, min, max, median）
  - 統計ユーティリティや設計原則（外部依存を避ける、DuckDB を用いる、ルックアヘッド防止）を適用。

- データ基盤ユーティリティ (kabusys.data)
  - calendar_management: JPX カレンダーの管理、営業日判定、next/prev_trading_day、get_trading_days、SQ日判定、夜間バッチ更新ジョブ calendar_update_job（J-Quants クライアント経由で差分取得・冪等保存）を実装。DB 存在なし時は曜日ベースフォールバックを採用。
  - pipeline / etl: ETLResult データクラスを追加（ETL 実行のメタ情報・品質問題・エラーを保持）。差分更新、バックフィル、品質チェック用の骨組みを用意。
  - jquants_client など外部データ取得クライアントを想定した設計（save_* 関数による冪等保存を前提）。

### 変更 (Changed)
- （初回リリースのため該当なし）  

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーの未設定時は明示的に ValueError を投げ、誤った実行を防止。
- .env の読み込み時に既存の OS 環境変数を保護するため protected set を導入（.env.local は override=True で上書き可能だが OS 環境変数は上書きされない）。

### 既知の制限 / 注意点 (Known issues / Notes)
- OpenAI 呼び出しは外部サービスへ依存しているため、API 負荷・レート制限の影響を受けます。リトライ・バックオフは実装済みだが、完全な可用性を保証するものではありません。
- DuckDB のバージョン差異に依存する SQL バインドの挙動（リスト型バインドなど）に配慮して、executemany を用いた個別 DELETE/INSERT を採用しています。
- news_nlp と regime_detector はそれぞれ独自の _call_openai_api を持ち、モジュール間でプライベート関数を共有しない設計です（テスト時はパッチ差替えを推奨）。
- time や外部 API 呼び出しを含む箇所はユニットテストではモック化する必要があります。
- strategy / execution / monitoring の詳細な実装は本リリースでの言及はあるが、個別の実装詳細はそれぞれのモジュールを参照してください（本CHANGELOGはコードベースから推測して作成しています）。

---

今後のリリースでは、以下を予定・検討しています:
- strategy / execution の注文ロジックと実際の発注統合（kabuステーション連携）の強化
- ai モジュールのパフォーマンス最適化、キャッシュ導入
- 品質チェックモジュールの拡張と ETL の自動通知連携 (Slack など)