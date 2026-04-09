# Changelog

すべての重要な変更履歴はここに記録します。本ファイルは「Keep a Changelog」規約に準拠しています。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]
- 次回リリースに向けた変更はここに記載します。

## [0.1.0] - 2026-04-09
### Added
- パッケージ基盤
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。バージョンは `0.1.0`。
  - 公開モジュール群の宣言: data, strategy, execution, monitoring（将来的な拡張箇所を想定）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート自動検出して読み込む自動ローダーを実装。
    - ルート検出は __file__ を起点に `.git` または `pyproject.toml` を探索するため配布後も安定。
    - 読み込み順: OS環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
  - .env のパース器を実装（コメント、export 形式、クォート内エスケープ対応）。
  - 設定取得用 `Settings` クラスを実装。J-Quants / kabuステーション / LINE / DB パス / Paper Trading 設定 / 監視閾値 / ログレベル 等のプロパティを提供。
  - 必須環境変数チェック（_require）と入力検証（環境値の許容値チェック）を実装。

- AI 支援モジュール（src/kabusys/ai）
  - ニュースNLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）で銘柄ごとのセンチメントを算出。
    - バッチ処理（最大20銘柄/チャンク）、記事数・文字数トリム、レスポンス検証、スコアのクリップ（±1.0）を実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装。失敗時は安全にスキップして継続。
    - レスポンスの復元ロジック（JSON前後の余計なテキストから {} を抽出）等の堅牢性向上処理を実装。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み件数を返す。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - OpenAI 呼び出しは専用の内部実装を持ち、リトライ・フェイルセーフ（失敗時 macro_sentiment=0.0）を備える。
    - DuckDB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。
  - 共通設計上の方針:
    - OpenAI API キーを引数または環境変数 `OPENAI_API_KEY` で解決。
    - テスト容易性のため内部の API 呼び出し関数を差し替え可能に実装（patch を利用可能）。

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーを取り扱うユーティリティ群を実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar テーブルがない場合は曜日ベースのフォールバック（週末を非営業日）を行い、一貫した挙動を保証。
    - 夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得し冪等保存を行う。バックフィル／健全性チェックを実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - 差分取得・保存・品質チェックの骨子を実装。
    - ETLResult データクラスを公開（src/kabusys/data/etl.py で再エクスポート）。ETL の取得件数・保存件数・品質問題・エラーを集約し、辞書変換メソッドを備える。
    - J-Quants クライアント（jquants_client）および quality モジュールとの連携を想定した設計。

- Research / ファクター計算（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、ma200 偏差）、Volatility（20日 ATR、相対 ATR、出来高/売買代金の指標）、Value（PER/ROE）などの計算を実装。DuckDB の SQL ウィンドウ関数を活用。
    - データ不足時の None 扱いや、スキャン範囲バッファ等の堅牢性を考慮。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、rank ユーティリティ、統計サマリー（factor_summary）を実装。
    - pandas など外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージで関連関数を __all__ により公開（zscore_normalize を data.stats から再利用）。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Security
- 環境変数の自動読み込みにおいて、OS 環境変数を保護するため .env の上書きロジックに protected set を導入（環境上書きの安全化）。
- OpenAI API 呼び出し失敗や応答パース失敗時は例外を全体に投げずフェイルセーフで継続する設計（誤った外部依存でプロセス全体が停止しないように配慮）。

### Notes / 実装上の重要事項
- ルックアヘッドバイアス防止のため、いずれの分析関数（score_news, score_regime, 各種ファクター計算等）も内部で datetime.today() / date.today() を直接参照せず、必ず外部から渡された target_date を基準に処理します。
- DuckDB を主要なデータ格納・処理エンジンとして想定。SQL はウィンドウ関数を多用しパフォーマンスを考慮した実装。
- AI 系処理は JSON Mode を利用し、LLM 応答の厳密な構造を前提に検証処理を行うことで誤出力耐性を高めています。
- DB への書き込みは可能な限り冪等（DELETE→INSERT や ON CONFLICT 相当）に実装しており、部分失敗時の既存データ保護に配慮しています。

---

今後の追加予定（例）
- execution / strategy / monitoring の具体実装（注文執行・ストラテジーインターフェース・実行監視）
- テストカバレッジの整備、CI ワークフローでの DuckDB テストデータセット導入
- J-Quants / kabu ステーション等のクライアント実装の充実（現在は外部モジュール参照を想定）

参考: 本リリースはソース内コメント・ドキュメント（StrategyModel.md, DataPlatform.md 等の設計記述）に基づき機能を実装しています。