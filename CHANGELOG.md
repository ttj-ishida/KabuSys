# CHANGELOG

すべての変更は Keep a Changelog 準拠の形式で記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- なし

## [0.1.0] - 2026-04-03
初期リリース。日本株自動売買システムのコアライブラリを実装しました。主要機能は以下のとおりです。

### Added
- パッケージ初期化
  - kabusys パッケージの基本定義を追加。__version__ = "0.1.0" を設定し、主要サブパッケージ（data, research, ai, 等）をエクスポート。

- 設定 / 環境変数管理（kabusys.config）
  - .env および .env.local ファイルからの自動読み込みを実装（OS 環境変数優先、.env.local は上書き）。
  - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - export KEY=val 形式やクォート・エスケープ・インラインコメントの取り扱いを考慮した .env パーサを実装。
  - 必須環境変数取得ヘルパー _require を提供（未設定時に ValueError を送出）。
  - 各種設定プロパティを実装（J-Quants / kabu API / LINE トークン / DB パス / 監視関連閾値 / 環境モードとログレベルの検証等）。
  - KABUSYS_ENV と LOG_LEVEL の許容値検証を実装（無効値は ValueError）。

- データプラットフォーム（kabusys.data）
  - ETL 用インターフェース ETLResult を追加（kabusys.data.pipeline から再エクスポート）。
  - pipeline モジュール:
    - ETLResult dataclass を実装（取得件数、保存件数、品質問題、エラーの集約と to_dict サポート）。
    - 差分取得・バックフィルの方針を実装（最小日付、デフォルトバックフィル日数、品質チェック連携の設計）。
    - DuckDB を前提としたテーブル存在チェック等のユーティリティを実装。
  - calendar_management モジュール:
    - market_calendar を用いた営業日判定ロジックを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar 未取得時の曜日ベースフォールバック（週末を休場扱い）を実装。
    - calendar_update_job を実装（J-Quants クライアント経由で差分取得、バックフィル、健全性チェック、冪等保存）。
    - 最大探索日数やバックフィル・先読み等の安全パラメータを導入。

- 研究モジュール（kabusys.research）
  - ファクター計算（factor_research）:
    - モメンタム: mom_1m / mom_3m / mom_6m、ma200_dev（MA200乖離）を DuckDB SQL で算出する calc_momentum を実装。データ不足時の扱い（None）や営業日スキャンバッファを考慮。
    - ボラティリティ/流動性: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を算出する calc_volatility を実装。true_range の NULL 伝播制御を行い正確なカウントを実装。
    - バリュー: raw_financials から直近財務データを取得し PER / ROE を算出する calc_value を実装。EPS が 0/欠損の場合は None を返す。
  - feature_exploration:
    - 将来リターン算出: calc_forward_returns（任意ホライズンに対応、入力バリデーション、1クエリ実行による効率化）。
    - IC（Information Coefficient）計算: calc_ic（コードで結合しスピアマンのランク相関を計算、データ不足時は None）。
    - ランク関数 rank（同順位は平均ランク、丸めで ties 問題を回避）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median を計算）。
  - 研究ユーティリティの再エクスポート（zscore_normalize 等）。

- AI モジュール（kabusys.ai）
  - ニュース NLI / NLP（news_nlp）:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信して銘柄別センチメントスコアを ai_scores テーブルへ保存する score_news を実装。
    - タイムウィンドウ: JST 前日 15:00 ～ 当日 08:30（UTC 変換あり）を厳密に扱う calc_news_window を実装。
    - バッチサイズ、記事数・文字数上限、エクスポネンシャルバックオフ、API エラー（429/ネットワーク/タイムアウト/5xx）に対するリトライ実装。
    - レスポンスの厳格なバリデーション（JSON 抽出、results キーの有無、型検査、未知コードの無視、数値チェック、±1.0 でクリップ）。
    - 部分失敗時に他コードの既存スコアを保護するための DELETE → INSERT の冪等書き込みロジック。
    - テストのしやすさを考慮し _call_openai_api を抽象化（unittest.mock.patch で差し替え可）。
  - 市場レジーム判定（regime_detector）:
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とニュース LLM（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - ma200_ratio の計算、マクロキーワードでの raw_news フィルタ、LLM（gpt-4o-mini）呼び出しでの macro_sentiment 評価、スコア合成、閾値判定を含む。
    - LLM 呼び出し失敗・パース失敗時はフェイルセーフとして macro_sentiment=0.0 を使用。
    - market_regime への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）およびトランザクション失敗時のロールバック処理を実装。
    - API キー解決は引数優先、環境変数 OPENAI_API_KEY をフォールバック。

- エラー処理・設計方針
  - すべての推定・スコアリング系処理でルックアヘッドバイアスを避けるために datetime.today() / date.today() を直接参照しない設計を徹底。
  - 外部 API 失敗時は例外をそのまま上げずにフォールバック（スコア 0.0）して処理継続する箇所を多数実装（フェイルセーフ）。
  - DuckDB の実装差やバージョン差異（executemany の空リスト許容など）に配慮した実装を行い、互換性を向上。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため特記事項なし。
  - 注意: OpenAI / J-Quants 等の API キーは環境変数で管理する想定。シークレットの漏洩対策は呼び出し側で行ってください。

---

注記:
- 本 CHANGELOG はコードベースからの実装内容・設計意図をもとに推測して作成しています。実運用上の細かな仕様（スキーマ定義、外部クライアントの実装詳細、マイナー挙動）は実際の実装・ドキュメントを参照してください。