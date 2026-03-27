# CHANGELOG

すべての変更は Keep a Changelog の仕様に準拠します。  
このプロジェクトはセマンティックバージョニングを採用しています。

## Unreleased
- 次回リリースの変更点はここに記載します。

---

## [0.1.0] - 2026-03-27

初回リリース。日本株自動売買システム「KabuSys」の基礎機能群を追加しました。主な追加内容は以下の通りです。

### 追加 (Added)
- パッケージ基礎
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"
  - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ に追加

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - 自動ロードの無効化: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
    - プロジェクトルート検出: .git または pyproject.toml を起点に探索（CWD 非依存）
  - .env パーサーの強化
    - コメント行・空行無視、`export KEY=val` 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理やインラインコメント処理に対応
  - 環境変数取得ユーティリティ
    - 必須項目取得時のエラーチェック（_require）
    - 設定クラス Settings を提供（J-Quants, kabuステーション, Slack, DB パス, 環境/ログレベル検証など）
    - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - 環境値検証: KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL の検証

- AI (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を基に銘柄別にニュースを集約し OpenAI（gpt-4o-mini）でセンチメントを算出
    - バッチ処理: 最大 20 銘柄ごとに API 呼び出し
    - トークン肥大化対策: 1銘柄につき最大記事数・最大文字数を制限
    - JSON Mode 出力のバリデーションと復元処理（前後テキストが混入した場合の {} 抽出）
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ
    - フェイルセーフ: API エラー時は該当チャンクをスキップし処理継続
    - 結果書き込み: ai_scores テーブルに対して対象コードのみ置換（DELETE → INSERT、部分失敗の保護）
    - 公開 API: score_news(conn, target_date, api_key=None)
    - 時間ウィンドウ計算ユーティリティ: calc_news_window(target_date)

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム判定
    - マクロニュースは raw_news からキーワードで抽出（上限件数）し OpenAI でスコア化
    - LLM 呼び出しは JSON レスポンスを期待、リトライとフェイルセーフを備える（失敗時 macro_sentiment=0.0）
    - レジームは score をクリップしてラベル付け（bull / neutral / bear）
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）、失敗時は ROLLBACK を試行
    - 公開 API: score_regime(conn, target_date, api_key=None)

- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等の営業日判定ユーティリティ
    - market_calendar が未取得の場合は曜日ベース（土日除外）でフォールバック
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等保存
    - 健全性チェック、バックフィル、探索上限（_MAX_SEARCH_DAYS）を実装
  - ETL パイプライン基盤 (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult データクラスを公開（取得/保存件数、品質チェック結果、エラー一覧等を保持）
    - 差分更新・バックフィル・品質チェックを想定した設計
    - jquants_client 経由の保存（idempotent 保存）と品質問題の収集を想定

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER, ROE）、Volatility（20 日 ATR、流動性指標）を計算する関数を実装
    - DuckDB を用いた SQL 主体の実装（prices_daily / raw_financials のみ参照）
    - 関数: calc_momentum, calc_value, calc_volatility
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、統計サマリー（factor_summary）、ランク関数（rank）を実装
    - 外部依存（pandas 等）を持たない純 Python 実装
  - 研究用ユーティリティの再公開: kabusys.data.stats.zscore_normalize をエクスポート

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- （初回リリースのため該当なし）

---

## 補足 / 実装上の注意
- 多くのモジュールで「ルックアヘッドバイアス防止」の観点から datetime.today() や date.today() を直接参照しない設計を採用。すべての公開 API は target_date を引数に受け取り、過去データのみを参照するようにしています。
- OpenAI 連携は gpt-4o-mini を想定し、JSON Mode を利用して厳密な JSON 応答を期待する形で実装しています。API 失敗時はフォールバック動作を定義し、例外による処理停止を極力避ける設計です。
- DuckDB の実装差異（executemany の空リスト不可など）を考慮した互換性対策を行っています。
- DB 書き込みは冪等性を考慮し、DELETE→INSERT や ON CONFLICT 相当の保存を想定しています。トランザクション（BEGIN/COMMIT/ROLLBACK）を基本とします。
- 環境変数やログレベル、不正値に対する検証を行い、運用ミスを早期に検出するようにしています。

もしリリースノートに特定の変更点（バグ修正、挙動差分、互換性注意など）を追加したい場合は、該当ソースファイルや変更履歴の詳細を教えてください。