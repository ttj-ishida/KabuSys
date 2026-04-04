# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」 https://keepachangelog.com/ja/ に準拠しています。

現在のバージョン: 0.1.0

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-04

初回公開リリース。日本株自動売買フレームワークの基盤機能を実装しました。主な追加点・設計方針は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージ API として data, research, ai, monitoring, execution, strategy 等を想定した __all__ を定義。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ローダを実装。
  - プロジェクトルートの自動探索は .git または pyproject.toml を基準とするため、CWD に依存しない。
  - 読み込み順序: OS 環境変数 > .env.local（上書き）> .env（未設定のみセット）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - export KEY=val 形式およびシングル/ダブルクォート、エスケープ、インラインコメントに対応する .env パーサを実装。
  - override/protected 機能で OS 環境変数を保護しつつ .env.local で上書き可能。
  - Settings クラスを公開（J-Quants、kabu API、LINE、DB パス、監視設定、閾値、環境判定等のプロパティを提供）。
  - 環境変数のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を追加。未設定の必須値は ValueError を送出。

- データプラットフォーム (kabusys.data)
  - ETL パイプラインの結果を表す ETLResult データクラスを実装（品質問題・エラーの集約、to_dict サポート）。
  - pipeline モジュール（ETL のインターフェース）と基本ユーティリティを追加。
  - calendar_management モジュールを実装（JPX カレンダー管理、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day）。
    - market_calendar テーブルがない場合は曜日ベースのフォールバック（週末は非営業日）。
    - DB 登録値優先、未登録日は曜日フォールバックで一貫して処理。
    - カレンダー差分更新ジョブ（calendar_update_job）を実装。バックフィル・健全性チェック・J-Quants API 呼び出しラップを備える。
  - ETL 用の内部ユーティリティ（テーブル存在チェック、最大日付取得等）を用意。

- 研究機能 (kabusys.research)
  - factor_research モジュールを追加（モメンタム、ボラティリティ、バリュー、流動性等の定量ファクター計算）。
    - calc_momentum, calc_volatility, calc_value を実装（DuckDB の prices_daily / raw_financials を参照）。
    - 200日移動平均、各種リターン、ATR、出来高指標などを SQL + Python で計算。
  - feature_exploration モジュールを追加（将来リターン計算、IC 計算、統計サマリー、ランク変換）。
    - calc_forward_returns（複数ホライズンの将来リターン取得、入力検証あり）。
    - calc_ic（Spearman 相当のランク相関を実装、データ不足時は None を返す）。
    - factor_summary（count/mean/std/min/max/median の算出）。
    - rank ユーティリティ（同順位は平均ランクを採用、丸め処理で ties の検出を安定化）。
  - data.stats の zscore_normalize を再エクスポート。

- AI / ニュース NLP (kabusys.ai)
  - news_nlp モジュールを実装（raw_news + news_symbols を集約して OpenAI にバッチ送信し、銘柄別センチメントを ai_scores に保存）。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換した半開区間で扱う calc_news_window を提供）。
    - gpt-4o-mini の JSON mode を利用（response_format={"type": "json_object"}、temperature=0）。
    - 1 チャンクあたり最大 20 銘柄、1 銘柄あたり最大 10 記事／3000 文字でトリム。
    - レート制限(429)、ネットワーク断、タイムアウト、5xx に対する指数バックオフのリトライを実装。
    - レスポンスの堅牢なバリデーションを実装（JSON 抽出、results リストの検証、未知コード無視、数値変換、有限性チェック、スコアの ±1.0 クリップ）。
    - 部分成功時に既存スコアを保護するため、書き込みはコード絞り込み → DELETE（個別 executemany）→ INSERT の冪等処理。
    - テスト支援のため OpenAI 呼び出し箇所は差し替え可能（_call_openai_api を patch 可能）。
  - regime_detector モジュールを実装（ETF 1321 の 200 日 MA 乖離（70%）とマクロセンチメント（30%）を合成して日次市場レジームを判定）。
    - マクロ判定は raw_news からマクロキーワードでフィルタしたタイトルを gpt-4o-mini に渡し JSON をパース。
    - API 失敗時は macro_sentiment=0.0 のフェイルセーフを採用。
    - 合成スコアをクリップしてラベル付け（bull / neutral / bear）。
    - market_regime テーブルへは BEGIN / DELETE / INSERT / COMMIT の冪等書き込み。失敗時は ROLLBACK を行い上位へ例外を伝播。
    - OpenAI 呼び出しでのリトライ（RateLimit, 接続障害, タイムアウト, 5xx）を実装。

- 設計方針・運用考慮
  - すべての「ターゲット日」ベース処理（score_news, score_regime, factor 計算など）は datetime.today() / date.today() を内部で参照せず、呼び出し側が target_date を渡す形式で実装（ルックアヘッドバイアス防止設計）。
  - OpenAI 呼び出しは deterministic（temperature=0）で JSON フォーマットを期待しつつ、レスポンスの前後余計なテキスト混入にも耐える復元ロジックを備える。
  - DuckDB のバージョン差分（executemany の空リスト制約等）を考慮した安全な DB 書き込み戦略を採用。
  - ロギングとワーニングを多用し、外部 API 失敗時もプロセスを停止させずフェイルセーフで継続する設計。

### 変更 (Changed)
- （初版のため変更履歴はなし。将来のリリースで追加予定）

### 修正 (Fixed)
- （初版のため修正履歴はなし）

### セキュリティ (Security)
- OpenAI API キーは引数で注入可能（api_key 引数）か環境変数 OPENAI_API_KEY を利用。未設定時は ValueError を返すことでキー漏洩につながる誤動作を未然に防止。

### 既知の注意点 / 制約
- DuckDB に依存するため、動作には DuckDB Python バインディングが必要。
- OpenAI の JSON mode を前提としているが、サービス側の挙動変化に備えたパース耐性を実装しているものの、モデルや API の大幅な仕様変更は影響を与える可能性があります。
- calendar_update_job では J-Quants クライアント（kabusys.data.jquants_client）を使用します。外部 API キーやネットワークが必要です。
- monitoring / execution / strategy 等一部コンポーネントは参照用の API surface を用意していますが、本リリース時点で完全な実行系（発注ロジックや監視ループの実装）は限定的です。

---

将来のリリースでは、実行・監視系の完成、バックテスト・シミュレーションツール、より詳細な品質チェックの強化、CI テストカバレッジの拡大などを予定しています。