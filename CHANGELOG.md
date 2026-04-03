# Changelog

すべての変更は「Keep a Changelog」形式に準拠します。  
このプロジェクトの初回公開リリース履歴を以下に示します。

なお、日付はリリース日です。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-03

### Added
- パッケージ初期リリース（kabusys 0.1.0）
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

- 環境変数・設定管理
  - .env ファイル自動読み込み機構を実装（プロジェクトルート検出: .git / pyproject.toml を基準）。
  - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き許可）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いに対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB / 監視設定 / システム設定（KABUSYS_ENV・LOG_LEVEL 検証含む）をプロパティ経由で参照可能（src/kabusys/config.py）。

- AI（自然言語処理）モジュール
  - ニュース NLP スコアリング: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント ai_score を生成して ai_scores テーブルへ保存（バッチ・チャンク処理、JSON Mode、レスポンスバリデーション、±1.0 クリップ、リトライ/バックオフ対応）（src/kabusys/ai/news_nlp.py）。
  - 市場レジーム判定: ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して market_regime テーブルへ日次保存（冪等書き込み、API フェイルセーフ、リトライロジック）（src/kabusys/ai/regime_detector.py）。
  - AI 呼び出しはテスト用に差し替え可能な内部ラッパーを利用し、モジュール間でプライベート関数を共有しない設計。
  - LLM 応答のパース失敗や API エラー時はフェイルセーフでスコアを 0.0 として継続し、警告ログを出力。

- データプラットフォーム機能
  - ETL パイプラインの基盤と ETL 実行結果用データクラス（ETLResult）を追加（取得/保存/品質チェックの結果やエラー情報を格納）（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）。
  - 市場カレンダー管理: market_calendar を用いた営業日判定・次/前営業日取得・期間内営業日取得・SQ判定ロジックと、J-Quants からの差分取得を行う夜間バッチ（calendar_update_job）を実装。DB にデータがない場合は曜日ベース（土日除外）でフォールバック（src/kabusys/data/calendar_management.py）。
  - calendar_update_job はバックフィル、健全性チェック、冪等保存（jquants_client 経由）に対応。

- リサーチ / ファクター計算
  - ファクター計算モジュールを提供（モメンタム / ボラティリティ / バリューなど）。DuckDB を用いた SQL＋Python 実装で prices_daily / raw_financials に依存し、本番口座や発注 API とは切り離し（src/kabusys/research/factor_research.py）。
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離計算（データ不足時の扱い明示）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比など。
    - calc_value: PER（EPS が 0/欠損時は None）、ROE（raw_financials の最新レコードを結合）。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 将来リターン（複数ホライズン）を一括クエリで取得、horizons の妥当性検証。
    - calc_ic: スピアマンランク相関（Information Coefficient）計算（レコード結合・None 除外・十分なサンプル数チェック）。
    - rank: 同順位は平均ランクとするランク化ユーティリティ（丸めによる ties 対応）。
    - factor_summary: count/mean/std/min/max/median の統計サマリー計算。
  - z-score 正規化ユーティリティを data.stats より再エクスポート（src/kabusys/research/__init__.py）。

- DB / 実装方針
  - DuckDB を想定したクエリを多用（複雑ウィンドウ関数等）、埋め込み SQL と Python の組合せで高効率に処理。
  - すべての日付処理は date / naive datetime を用い、ルックアヘッドバイアスを避ける設計方針を徹底。
  - API キー未設定時は ValueError を送出する（明示的チェック）。

### Changed
- （初回リリースのため履歴変更なし）

### Fixed
- （初回リリースのため修正履歴なし）
  - ただし、API 呼び出し周りや DB 書込みではフェイルセーフ処理（ログ出力・0.0 フォールバック・ROLLBACK 保護など）を多用し、部分失敗がシステム全体を停止させない設計が導入されています。

### Security
- OpenAI / 外部 API のキーは Settings 経由で環境変数から取得する設計。ただしソースコード内に API キーをハードコーディングしないことを想定。
- デフォルトではローカルの API エンドポイントやファイルパスが設定されるため、運用時は環境変数で適切に上書きしてください（例: KABUSYS_ENV, LOG_LEVEL, OPENAI_API_KEY 等）。

### Notes / 既知事項
- ニュース集約ウィンドウや calendar_update_job の参照時間は UTC naive datetime を利用しており、JST ↔ UTC の変換はモジュール内で行われています。実行環境でのタイムゾーン依存に注意してください。
- DuckDB の executemany に空リストを渡せない制約に対応する実装（空チェック）を行っています。
- OpenAI API の呼び出しは標準的なエラー（429, ネットワーク断, タイムアウト, 5xx）に対するリトライ/バックオフ実装がありますが、運用ではレート制限やコスト管理に注意してください。
- 本リリースは「データ取得・解析・スコア算出」までを対象としており、実際の発注/執行（execution モジュールの公開等）や監視（monitoring）周りは将来的な拡張対象です（パッケージ __all__ に "execution", "monitoring" を含めているためインターフェース拡張が予定されています）。

-contributors-
初回リリースのコードベースに基づき CHANGELOG を作成しました。

--- 

（この CHANGELOG はコードベースから推測して作成しています。実際のリリース履歴や変更点と差異がある場合は本ファイルを適宜編集してください。）