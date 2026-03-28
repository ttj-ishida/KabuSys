# Changelog

すべての変更は Keep a Changelog の仕様に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-28
初回リリース。日本株向けの自動売買・データプラットフォーム用ライブラリの基礎機能を実装しました。主な追加点と設計方針は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージ初期構成を追加。公開対象モジュールとして data, strategy, execution, monitoring を想定。
  - __version__ を "0.1.0" に設定。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定をロードする設定管理モジュールを追加。
  - プロジェクトルート自動検出: .git または pyproject.toml を基準に探索（CWD に依存しない実装）。
  - .env/.env.local の読み込み順序および override / protected（OS 環境変数保護）の挙動を実装。
  - .env 解析で以下をサポート:
    - export KEY=val 形式
    - シングル／ダブルクォート、バックスラッシュエスケープ
    - インラインコメントの扱い（クォートの有無に応じた判定）
  - 環境変数必須チェック用の _require と Settings クラスを提供（J-Quants、kabu、Slack、DB パス、環境種別、ログレベル等）。

- ニュースNLP / AI (kabusys.ai)
  - news_nlp.score_news:
    - raw_news と news_symbols を集約し、OpenAI (gpt-4o-mini) JSON mode を用いて銘柄ごとのセンチメント（ai_score）を算出して ai_scores テーブルへ保存する機能を追加。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄当たりの最大記事数・文字数トリム、レスポンスバリデーション、スコア ±1.0 クリップを実装。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライと、非リトライエラー時はスキップして継続するフェイルセーフ方針を採用。
    - DuckDB に対する互換性考慮（executemany に空リストを渡さない等）。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（モジュール内プライベート関数を patch 可能）。
    - ニュース収集ウィンドウ calc_news_window を実装（JST基準: 前日 15:00 ～ 当日 08:30 → UTC で前日 06:00 ～ 23:30）。
  - regime_detector.score_regime:
    - ETF（コード 1321）の 200 日移動平均乖離と、マクロニュースの LLM センチメントを重み付け合成して日次の市場レジーム（bull / neutral / bear）を算出し market_regime テーブルへ冪等的に書き込む機能を追加。
    - MA 計算、マクロキーワードで絞った raw_news タイトル抽出、OpenAI 呼び出し（gpt-4o-mini）による JSON レスポンス解析、スコア合成、閾値判定を実装。
    - API エラー時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ実装。
    - OpenAI クライアントのエラー種類に応じたリトライ・待機ロジックを実装。

- 研究・ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離を計算（prices_daily を参照）。データ不足時の扱いを明示。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から取得した最新財務データと株価を組み合わせて PER / ROE を算出。
    - DuckDB を用いた SQL ベース実装で、外部 API へはアクセスしない設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンをまとめて取得するクエリを実装。
    - calc_ic: Spearman ランク相関（Information Coefficient）を計算するユーティリティを実装（欠損・同順位等の取り扱い含む）。
    - rank: 同順位は平均ランクで処理するランク化関数を実装（丸め処理で ties の誤差を吸収）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー機能を追加。
  - 研究用ユーティリティは標準ライブラリのみで依存を抑えた実装。

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - JPX マーケットカレンダー管理機能（market_calendar 参照/更新）を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定 API を提供。
    - DB データ優先、未登録日は曜日ベース（週末除外）のフォールバック、探索範囲上限による安全設計。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に更新する夜間バッチ処理を実装（バックフィル・健全性チェック付き）。
  - pipeline / etl:
    - ETLResult: ETL 実行結果を表す dataclass を公開（kabusys.data.ETLResult 経由で再エクスポート）。
    - ETL パイプラインの基本設計（差分更新・保存・品質チェック）骨格を実装。品質チェック結果（quality.QualityIssue）を集約して返す方針。
    - DuckDB 上での最大日付取得などのユーティリティを提供。
  - DuckDB を想定した SQL 実装と、J-Quants クライアントとの連携を想定した設計。

### Changed
- （初回リリースのため過去からの変更はなし）

### Fixed
- （初回リリースのため過去からの修正はなし）

### Notes / 設計上の重要なポイント
- ルックアヘッドバイアス対策:
  - どのモジュールも内部で datetime.today() や date.today() を参照しない設計（外部から target_date を注入する形）。データ/モデル評価におけるルックアヘッドを避ける方針を明記。
- フェイルセーフ方針:
  - OpenAI API に依存する処理は、API エラー時にスキップまたはデフォルト値（例: macro_sentiment = 0.0）で継続する実装。
- テスト容易性:
  - OpenAI への呼び出し箇所は _call_openai_api のような内部関数でラップし、unittest.mock.patch で差し替え可能にしている。
- DuckDB 互換性:
  - executemany に空リストを渡すと失敗するバージョンへの対応など、実運用での互換性に配慮した実装。
- ロギング:
  - 各処理は詳細な info/debug/warning ログを出力するよう実装されており、問題発生時の調査を容易にしている。

---

今後の予定（例）
- strategy / execution / monitoring の具体的な実装追加（発注ロジック、監視・アラート機能等）
- J-Quants / kabu ステーション用クライアントの詳細実装と統合テスト
- 性能改善（大規模データセットでの ETL 最適化、バッチ並列化）

お問い合わせや改善提案があれば Issue を作成してください。