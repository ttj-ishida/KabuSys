# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従って管理されています。  
リリース日付はコードベースの現時点の推測に基づいています。

## [Unreleased]
- 現在未リリースの変更はありません。

## [0.1.0] - 2026-03-27
最初の公開リリース。日本株自動売買システム「KabuSys」のコア機能群を実装。

### Added
- パッケージ基盤
  - パッケージ初期化: kabusys のトップレベル __version__ を "0.1.0" に設定。主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。
- 設定管理（kabusys.config）
  - .env/.env.local ファイルおよび OS 環境変数から設定を自動ロードする機能を実装。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env 解析の強化:
    - export プレフィックス対応（export KEY=val）
    - シングル/ダブルクォートのエスケープ対応
    - インラインコメント処理（クォート外の '#' をコメントとして扱うなど）
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準に決定）し、CWD に依存しない自動読み込みを実現。
  - 必須環境変数取得ヘルパー `_require` と Settings クラスを提供（J-Quants・kabuステーション・Slack・DB パス・ログレベル等の設定をプロパティで公開）。
  - 環境値のバリデーション（KABUSYS_ENV / LOG_LEVEL の許容値チェック）とユーティリティプロパティ（is_live / is_paper / is_dev）を追加。

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を使い、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）へバッチ送信しセンチメントを計算する機能を実装。
    - 時間ウィンドウ計算（日本時間基準）を提供する calc_news_window を実装。
    - バッチ処理（最大 20 銘柄/回）、1 銘柄あたりの記事数・文字数上限、レスポンスの厳格なバリデーション、スコアの ±1.0 クリップを実装。
    - ネットワーク/レート制限/サーバーエラーに対する指数バックオフリトライを実装。API キー注入をサポート（引数 or 環境変数）。
    - テスト用フック: OpenAI 呼び出し部分を patch で差し替え可能（_call_openai_api の設計）。
    - ai_scores テーブルへの冪等的な書き込み（対象コードのみ DELETE → INSERT）。DuckDB の executemany 空リスト制約への対応。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で market_regime を生成する機能を実装。
    - マクロキーワードによる raw_news フィルタ、OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment 評価、スコア合成・ラベリング（bull/neutral/bear）を実装。
    - API エラーやパース失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフを実装。
    - DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等性を確保。失敗時は ROLLBACK を試行し例外を伝播。
    - テスト性を考慮し、OpenAI 呼び出しを独立実装（news_nlp から共有しない設計）。

- データ処理（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar）を扱うユーティリティを実装（営業日判定 / next/prev / 範囲内営業日の取得 / SQ 日判定）。
    - market_calendar の不在時は曜日ベースのフォールバック（週末を非営業日）を一貫して使用。
    - calendar_update_job を実装し J-Quants API から差分取得 → 保存（バックフィル・健全性チェックを含む）を行う。J-Quants クライアントは jquants_client を利用。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを導入し、ETL 実行のメタ情報（取得/保存件数、品質問題、エラー概要など）を集約できるようにした。
    - 差分更新・バックフィル・品質チェックの方針を反映したユーティリティと DB 存在確認ロジックを実装。
    - jquants_client と quality モジュールを組み合わせた差分取得 → 保存のフローを想定した設計。

- 研究用機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR（20 日）、流動性指標（平均売買代金、出来高比率）、バリュー（PER, ROE）などのファクター計算を実装。
    - DuckDB に対する SQL + Python の組合せで高速に計算する設計。データ不足時の None 扱いを明確化。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、rank 関数、ファクター統計サマリーを実装。
    - pandas 等に依存しない純標準実装。
  - データ統計ユーティリティ（kabusys.data.stats）からの zscore_normalize を再エクスポート。

### Changed
- ログ出力とエラーハンドリングを各モジュールで整備
  - API 呼び出し失敗時やパースエラー時のログメッセージを詳細化し、処理継続の方針（フェイルセーフ）を統一。
  - DB 書き込み失敗時に ROLLBACK を試みるなどトランザクション安全性を強化。

### Fixed
- OpenAI レスポンスのパース堅牢化
  - JSON Mode 使用時にも前後に余計なテキストが混入するケースを補正して JSON を復元する処理を追加（news_nlp）。
  - レスポンス内のコードが整数で返るケースを文字列化して照合するように修正（news_nlp）。

### Security
- API キーの必須化
  - OpenAI API キーが未設定の場合は ValueError を送出して明示的に失敗する設計（score_news / score_regime）。安全な運用を促進。

### Notes / Developer guidance
- 必須環境変数（例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings のプロパティで必須扱い。
- DB スキーマ前提
  - 一部処理は DuckDB の特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）存在を前提としているため、テスト時はモック DB または整合したスキーマを用意すること。
- テスト性
  - OpenAI への実ネットワーク呼び出しはテスト時に差し替え可能（各モジュールの _call_openai_api を patch する設計）。
- Look-ahead バイアス対策
  - 各アルゴリズムは内部で datetime.today()/date.today() を参照しないか、引数で基準日を受け取るなどしてルックアヘッドを防止する設計。

### Breaking Changes
- なし（初期リリースのため該当なし）。

---

（注）上記はソースコードから推測して作成した変更履歴です。実際のリリースノート作成時はリリースの意図・日付・関連 Issue/PR 等を明記することを推奨します。