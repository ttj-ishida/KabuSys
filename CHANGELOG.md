# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このファイルはコードベース（src/kabusys 配下）の現在の状態から推測して作成した変更履歴です。

## [Unreleased]
（次回リリースに向けた未確定の変更やメモを記載するセクション）

- なし

## [0.1.0] - 2026-03-29
初回公開リリース。パッケージのコア機能（データ取得・ETL、マーケットカレンダー管理、リサーチ用ファクター計算、AI ベースのニュース解析/レジーム判定、設定管理等）を実装。

### Added
- パッケージ初期化
  - kabusys パッケージを追加し、__version__ = "0.1.0" を設定。主要サブパッケージ（data, research, ai, monitoring, strategy, execution 等）を __all__ で公開予定の要素として定義（現状は一部モジュール実装）。

- 環境設定管理（kabusys.config）
  - .env ファイルと環境変数を統合して読み込む自動ローダーを実装。プロジェクトルート判定は .git または pyproject.toml を基準に実行。
  - .env ファイルパーサーを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応）。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、アプリケーションで利用する主要設定（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、環境種別、ログレベル判定等）をプロパティとして取得可能に。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL などの許容値チェック）および必須環境変数未設定時は ValueError を送出する仕組みを追加。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）の Chat Completions（JSON mode）でセンチメントスコアを計算して ai_scores テーブルへ書き込む機能を実装。
  - タイムウィンドウ（JST: 前日15:00〜当日08:30）を計算する calc_news_window を提供。
  - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの最大記事数/文字数トリム、API レート制限・ネットワーク・5xx に対するエクスポネンシャルバックオフリトライ、レスポンスの厳密なバリデーション、スコアの ±1.0 クリップなどを実装。
  - API 呼び出し点はテスト容易性のため差し替え可能（内部 _call_openai_api を patch してモック化可能）。
  - エラー耐性: API 呼び出しやパース失敗時は該当チャンクをスキップし、他の銘柄処理を継続（フォールセーフ設計）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - prices_daily からの MA200 比率計算、raw_news からマクロキーワード抽出、OpenAI へのセンチメント問い合わせ、スコア合成・閾値判定、market_regime テーブルへの冪等的書込（BEGIN / DELETE / INSERT / COMMIT）を実装。
  - API 呼び出し失敗時は macro_sentiment=0.0 で継続するフェイルセーフ、リトライロジック、JSON パースの堅牢化を提供。
  - テストしやすい設計（_call_openai_api の差し替えが可能）。

- データプラットフォーム / カレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダー管理（market_calendar）向けのユーティリティ群を提供:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
  - DB 登録値を優先しつつ、未登録日は曜日ベース（土日）でフォールバックする一貫した判定ロジックを実装。
  - calendar_update_job を追加し、J-Quants API クライアント経由で差分取得→冪等保存（バックフィル、健全性チェック含む）を行う。

- ETL パイプライン（kabusys.data.pipeline / etl）
  - ETLResult データクラスを提供し、ETL 実行結果の集約（取得数・保存数・品質チェック結果・エラーメッセージ等）を記録可能に。
  - 差分更新・バックフィル・品質チェックを想定したユーティリティ関数群の土台を実装（jquants_client / quality モジュールと連携する設計）。

- リサーチ（kabusys.research）
  - ファクター計算・特徴量探索モジュールを実装:
    - factor_research: calc_momentum（1M/3M/6M リターン, MA200 乖離）, calc_volatility（ATR20, avg_turnover, volume_ratio）, calc_value（PER, ROE）
    - feature_exploration: calc_forward_returns（将来リターン）, calc_ic（スピアマンランク相関 / IC）, factor_summary（基本統計量）, rank（同順位は平均ランク）
  - DuckDB を利用して SQL + Python で効率的に計算する設計。欠損やデータ不足に対する扱い（None 戻し）を明確に定義。

- パッケージ内モジュール公開調整
  - research と ai パッケージで主要関数を __all__ により再エクスポート（外部利用インターフェースの明示）。

### Changed
- （初回リリースのため変更履歴はなし。ただし設計方針として以下を明示）
  - ルックアヘッドバイアス回避: news_nlp / regime_detector 等のモジュールは内部で datetime.today()/date.today() を直接参照しない設計。ターゲット日引数を必須にして、外部から指定することで過去データのみを利用するようにしている。
  - DuckDB 互換性対策: executemany の空リスト問題や list バインドの違いを考慮した実装（空チェックや個別 DELETE の利用）。

### Fixed
- （初回リリースのため修正履歴はなし）

### Security
- OpenAI API キーは関数引数で注入可能。環境変数 OPENAI_API_KEY に依存するが、必須未設定時は明示的に ValueError を送出して通知する。

### Notes / Implementation details（重要な設計上の注意）
- .env 自動ロードはプロジェクトルート検出に依存。パッケージ配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して無効化可能。
- 多くの処理は DuckDB の特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials など）を前提としている。DB スキーマが用意されていない場合は値が返らない / None となる箇所がある。
- OpenAI 呼び出し部分はリトライ・バックオフやレスポンス検証を備えるが、外部 API の制約により部分的なスコア欠損が起きうる。ETL や書き込みは部分失敗時に既存データを不必要に消さないよう設計している（書き込み対象コードの限定削除など）。
- market/calendar 関連は market_calendar が空の場合に曜日ベースでフォールバックするため、初回導入時は calendar_update_job により calendar を取得・保存することを推奨。

---

注: 本 CHANGELOG はコードの実装内容から推測して作成しています。将来的なリリースでは実際のコミット履歴・イシューに基づいて更新してください。