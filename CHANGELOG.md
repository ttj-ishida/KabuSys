# Changelog

すべての重要な変更点はこのファイルに記録します。本ファイルは「Keep a Changelog」仕様に準拠します。  
バージョン番号は package 内の __version__（src/kabusys/__init__.py）に対応します。

※ 日付はリリース日です。

## [Unreleased]
- 次回リリースに向けた未確定の変更点やマイナー修正をここに記載します。

## [0.1.0] - 2026-04-04
初回公開リリース。日本株自動売買・データ基盤・リサーチ用のユーティリティ群を提供します。

### Added
- パッケージ基本情報
  - kabusys パッケージとして公開（__version__ = 0.1.0）。
  - パッケージの公開インターフェースに data, strategy, execution, monitoring を含める。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイル自動読み込み機能（プロジェクトルート推定: .git または pyproject.toml）を実装。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env の行パーサ実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント考慮）。
  - Settings クラスを実装し、J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 実行環境（development/paper_trading/live）等のプロパティを提供。
  - 必須環境変数未設定時は分かりやすい ValueError を発生させるヘルパーを追加。

- AI モジュール（src/kabusys/ai）
  - ニュースセンチメント集約（news_nlp.score_news）
    - raw_news と news_symbols を用いて銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを評価。
    - バッチ処理（最大20銘柄/チャンク）、記事数・文字数トリム、JSON Mode でのレスポンス検証を実装。
    - レスポンス検証ロジック（JSON 抽出、results リスト検査、コード整合性、数値チェック、±1.0 でクリップ）。
    - 取得成功銘柄のみ ai_scores テーブルへ DELETE → INSERT の冪等更新。
    - ネットワーク/レート制限/5xx などに対するリトライ（指数バックオフ）と、API失敗時は該当チャンクをスキップするフェイルセーフ。
    - DuckDB 0.10 の executemany の制約（空リスト不可）に配慮した実装。
  - 市場レジーム判定（ai.regime_detector.score_regime）
    - ETF 1321 の 200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - prices_daily / raw_news を参照して ma200_ratio の計算、マクロ記事抽出、OpenAI 呼び出し（gpt-4o-mini & JSON mode）を行い、market_regime テーブルへ冪等書き込み。
    - API の失敗やパース失敗時は macro_sentiment=0.0（中立）にフォールバックすることで処理継続性を確保。
    - OpenAI 呼び出しはリトライ実装（RateLimit/Timeout/5xx に対するバックオフ）を持つ。

- データ / ETL（src/kabusys/data）
  - ETLResult（data.pipeline.ETLResult）をデータクラスとして実装・公開（etl.py で再エクスポート）。
  - pipeline モジュールに差分取得・保存・品質チェックを想定した ETL の骨格（データ構造、ユーティリティ）を実装。
  - 市場カレンダー管理（data.calendar_management）
    - market_calendar を基に営業日判定・前後営業日取得・期間内営業日取得・SQ判定を実装。
    - calendar_update_job による J-Quants からの差分取得と冪等保存を実装。バックフィル・健全性チェックあり。
    - DBにデータがない場合は曜日ベース（土日非営業）でフォールバックする一貫した挙動を提供。

- リサーチ（src/kabusys/research）
  - ファクター計算（research.factor_research）
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日ATR、相対ATR）、Value（PER, ROE）、Liquidity 指標を計算する関数を実装。
    - DuckDB の window 関数を利用した効率的クエリ実装。データ不足時は None を返す方針。
  - 特徴量探索（research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）
    - IC（Spearman のランク相関）計算（calc_ic）
    - ファクター統計サマリー（factor_summary）
    - ランク付けユーティリティ（rank） — ties を平均ランクで処理し丸めで安定化。
  - zscore_normalize を data.stats 経由で再エクスポートするインターフェースを提供。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- 環境変数取り扱いにおいて OS 環境変数を保護するため .env ロード時に既存のキーを保護（protected set）する仕組みを導入。

### Design / Implementation Notes（設計上の重要ポイント）
- ルックアヘッドバイアス防止: 各モジュール（news_nlp, regime_detector, research 等）は内部で datetime.today()/date.today() を参照せず、外部から与えられた target_date のみを基準に処理を行う。
- 冪等性とトランザクション: DB への書き込みは基本的に BEGIN / DELETE / INSERT / COMMIT のパターンで冪等に行う。失敗時は ROLLBACK を試行し、RB も失敗した場合は警告ログ。
- フェイルセーフ: 外部 API（OpenAI, J-Quants）失敗時は処理継続のため安全側のデフォルト値（例: macro_sentiment=0.0）を使う設計。
- OpenAI 呼び出し: gpt-4o-mini を想定、JSON Mode を利用。API エラーに対してリトライ（指数バックオフ）、レスポンス検証を厳格に実施。
- DuckDB 互換性配慮: executemany に空リストを渡さない等、実装上の細かな互換性対策あり。
- ロギング: 主要処理で info/debug/warning を出力し問題解析を容易に。

### Known limitations / TODO
- ファクター: PBR・配当利回り等は現バージョンでは未実装（calc_value のドキュメント参照）。
- news_nlp/regime_detector の OpenAI 呼び出しはテスト可能性のため差し替え可能（モジュール内の _call_openai_api をモックする想定）。
- strategy / execution / monitoring の具象実装（発注ロジック・監視サービス等）はこのリリースでは含まれていない（パッケージエクスポートは示されるが実装は別モジュールに依存する想定）。

---

履歴の書式やセクションの追加・修正、あるいは過去リリースの追記が必要な場合はお知らせください。