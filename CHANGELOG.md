# Changelog

すべての重要な変更点は Keep a Changelog のガイドラインに従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注: 以下の履歴はリポジトリ内のコード内容から推測して作成した初期リリース向けの要約です。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買 / データ基盤 / 研究用ユーティリティ群のコア機能を実装。

### Added
- パッケージ基盤
  - パッケージのエントリポイントを追加（src/kabusys/__init__.py）。公開サブパッケージ: data, strategy, execution, monitoring。
  - バージョン情報: 0.1.0 を設定。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルと OS 環境変数の統合読み込み機能を実装。
    - プロジェクトルートを .git / pyproject.toml を基準に探索して自動読込。
    - 読み込み順: OS 環境変数 > .env.local > .env（.env.local は上書き）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env パーサーを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
  - 環境変数の必須チェック用 _require と Settings クラスを提供。J-Quants / kabu / Slack / DB パス等の設定アクセスプロパティを実装。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）と便利な is_live/is_paper/is_dev 判定。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を基に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄単位のセンチメント（ai_score）を算出するスコアリング機能を実装。
  - 日次のニュースウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）計算ユーティリティ calc_news_window を実装。
  - バッチ処理（1コール最大 20 銘柄）、記事トリム（最大記事数・最大文字数）によりトークン肥大化対策を実施。
  - OpenAI API 呼び出しのリトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで処理。
  - JSON Mode のレスポンス検証と堅牢なパースロジック（前後の余計なテキスト抽出、型チェック、未知コード無視、スコアのクリップ）。
  - テスト容易性のため _call_openai_api を patch できる設計。
  - スコアを ai_scores テーブルへ冪等的に置換（DELETE → INSERT）。部分失敗時に他銘柄の既存スコアを消さない戦略。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull / neutral / bear）を算出して market_regime テーブルへ書き込む機能を実装。
  - prices_daily からの MA 計算、raw_news からマクロキーワード抽出、OpenAI (gpt-4o-mini) を用いた macro_sentiment 評価、スコア合成、冪等書き込みを含む一連の処理を実装。
  - API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフを備える。
  - テスト用に _call_openai_api を差し替え可能に設計。

- データ関連（src/kabusys/data/*）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルに基づき営業日・SQ判定、next/prev/get_trading_days 等のユーティリティを実装。
    - DB データがない箇所は曜日ベース（週末除外）でフォールバックする一貫したロジックを実装。
    - JPX カレンダーを J-Quants から差分取得し更新する夜間バッチ calendar_update_job を実装（バックフィル & 健全性チェック内蔵）。
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py, etl.py）
    - ETL 実行結果を保持する ETLResult データクラスを追加（品質チェック結果・エラー一覧を含む）。
    - 差分取得、バックフィル、保存（jquants_client 経由で冪等保存）、品質チェックのフローを想定したユーティリティを実装。
    - テーブル存在チェック、最大日付取得などの内部ユーティリティを実装。
    - etl モジュールから ETLResult を公開（再エクスポート）。

- 研究（research）モジュール（src/kabusys/research/*）
  - factor_research: Momentum / Volatility / Value ファクター計算関数を実装。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials を参照して PER / ROE を計算（EPS=0/欠損は None）。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、統計サマリー（factor_summary）、rank ユーティリティ等を実装。
  - data.stats の zscore_normalize を再エクスポートする公開 API を提供。

### Changed
- なし（初回リリースのため新規実装中心）。ただし設計上以下の方針を採用:
  - すべての日次処理で datetime.today()/date.today() の直接参照を避け、target_date に依存することでルックアヘッドバイアスを防止。
  - DuckDB を中心に SQL + Python による集計を行い、外部（取引）API へのアクセスを研究/データ処理コードから分離。

### Fixed
- 仕様的な堅牢化・例外処理を実装（実バグ修正ではなく堅牢化として）
  - DB 書き込み失敗時のトランザクション ROLLBACK の保証と警告ログ。
  - OpenAI API レスポンスのパース失敗や API エラーをフェイルセーフ（ゼロやスキップ）にフォールバックすることでバッチ全体の失敗を回避。
  - DuckDB の executemany に対する空リストの制約考慮（空の場合は実行をスキップ）。

### Security
- なし（現状のコードから明示的なセキュリティ修正は検出できません）。ただし環境変数の扱いで OS 環境変数を保護する protected キーセットを導入。

### Notes / Implementation details
- OpenAI の使用:
  - gpt-4o-mini を想定、JSON Mode を利用した厳密な JSON 出力を前提。
  - リトライやバックオフ、5xx とそれ以外の区別、最大リトライ回数等の実装により実運用での安定性を考慮。
- テスト性:
  - AI 呼び出しの内部呼び出し関数（_call_openai_api）を unittest.mock で差し替え可能にしてユニットテストを容易化。
- データベース操作:
  - 各種書き込みは冪等性を意識（DELETE → INSERT、ON CONFLICT 想定の save_* 関数）し、部分失敗が他データを破壊しないように設計。

---

今後のリリース案（例）
- Unreleased:
  - strategy / execution / monitoring サブパッケージの実稼働向け実装（注文実行、ポートフォリオ管理、アラート）。
  - テストカバレッジ強化、CI 設定、ドキュメント整備。
  - セキュリティチェック（秘匿情報の safer handling、機密情報のログ出力防止）。

（この CHANGELOG はコード内容から推測した概要を元に作成しています。差異がある場合は実際のコミット履歴に合わせて調整してください。）