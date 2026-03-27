# CHANGELOG

すべての notable な変更点は Keep a Changelog の形式で記載します。初期リリース v0.1.0 としてコードベースの機能・実装を推測してまとめています。

全般的な方針:
- 日付や現在時刻を直接参照する呼び出し（datetime.today() / date.today()）を避け、ルックアヘッドバイアスを排除する設計が徹底されています。
- OpenAI 呼び出しや外部 API 呼び出しはフェイルセーフ（失敗時にスキップして継続）とし、冪等性やリトライ/バックオフ戦略が実装されています。
- DuckDB を主データストアとして想定した実装（互換性・SQL 実装上の注意点あり）。

## [0.1.0] - 2026-03-27

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ基礎 (src/kabusys/__init__.py) とバージョン情報を追加。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートの検出は .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - .env パース処理を強化: export プレフィックス対応、クォート付き値（バックスラッシュエスケープ対応）、インラインコメントの取り扱い。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境・ログレベル等の取得ロジックを集中管理。必須環境変数未設定時は明示的なエラーを発生させる。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。

- ニュース NLP（OpenAI ベース）(src/kabusys/ai/news_nlp.py)
  - raw_news と news_symbols を元にニュースを銘柄別に集約し、OpenAI（gpt-4o-mini）の JSON mode によるセンチメントスコアリングを実装。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を提供する calc_news_window。
  - バッチ処理（最大 20 銘柄／リクエスト）、記事数・文字数トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）によるトークン肥大化対策。
  - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）と指数的バックオフを実装。
  - レスポンスの厳格なバリデーションとスコアクリップ（±1.0）。部分成功時は既存スコアを保護するために書き込み対象コードのみ置換（DELETE → INSERT の冪等実装）。
  - テスト容易性のため OpenAI 呼び出し部分は差し替え可能（ユニットテストで patch できる設計）。

- 市場レジーム判定モジュール (src/kabusys/ai/regime_detector.py)
  - ETF 1321（Nikkei 225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
  - prices_daily / raw_news を参照して MA200 乖離計算、マクロ記事の抽出、OpenAI によるセンチメント評価を実行。
  - API エラー時やパース失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ実装。
  - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK の安全処理を実装。

- リサーチ・ファクター計算 (src/kabusys/research/)
  - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）などのモメンタム系ファクターを計算。
  - calc_volatility: 20 日 ATR（atr_20, atr_pct）、20 日平均売買代金、出来高比率などを計算。
  - calc_value: raw_financials を利用した PER（EPS ベース）、ROE を計算（target_date 以前の最新財務データを使用）。
  - いずれも DuckDB 接続を受け取り SQL で完結し、本番取引 API に影響を与えない設計。
  - research パッケージの __init__ で主要関数を再エクスポート。

- 特徴量探索 / 統計機能 (src/kabusys/research/feature_exploration.py)
  - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）における将来リターンを一括で取得。
  - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
  - rank: 同順位は平均ランクで扱うランク変換ユーティリティ（丸めによる ties 対応）。
  - factor_summary: count/mean/std/min/max/median の統計サマリーを計算。
  - pandas 等の外部ライブラリに依存しない純標準ライブラリ実装。

- データプラットフォーム機能 (src/kabusys/data/)
  - calendar_management: JPX カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）と夜間の calendar_update_job を実装。market_calendar が未取得時は曜日ベースでフォールバックする設計。
  - pipeline / etl: ETLResult データクラス（target_date・取得数・保存数・品質問題・エラー等）を実装し、パイプライン用の結果型を公開。差分取得、バックフィル、品質チェックの方針に準拠した設計。
  - DuckDB 互換性に配慮したユーティリティ（テーブル存在チェック、最大日付取得、executemany の空リストの扱い回避など）。

- モジュールの公開整理
  - ai.__init__.py、research.__init__.py、data/etl.py などで主要 API を再エクスポートし、使いやすいパブリック API を提供。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）
  - ただし多くのモジュールでエラーハンドリングや ROLLBACK 保護、API レスポンスパース失敗時のフォールバックなどを実装して堅牢性を向上。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キー取得は引数注入または環境変数 OPENAI_API_KEY により明示的に行う設計。未設定時は ValueError を発生させ、意図せぬキー漏洩を防止。
- .env 自動読み込みは環境で制御可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）でテスト時の外部影響を抑制。

---

注意事項・実装上の留意点（ドキュメント的補足）
- DuckDB を利用した SQL 実装ではバインドリストや executemany の扱いにバージョン差異があるため、空リスト送信の回避や個別 DELETE を用いるなどの互換性対策が組み込まれています。
- OpenAI は JSON mode を前提とするプロンプト設計（厳密な JSON 出力を期待）ですが、現実のレスポンスで前後テキストが混入するケースを考慮し、最外の {...} を抽出して復元するロジックを含みます。
- 日付処理はすべて date / naive datetime を用いる方針（タイムゾーンの混入を避ける）。ニュースウィンドウは JST を基準に UTC naive datetime に変換して DB と比較します。
- テスト容易性を考慮し、OpenAI 呼び出し関数はモジュール内で抽象化されており unittest.mock.patch による差し替えが想定されています。

もし特定の変更点をより詳しく記載（例: 各関数の戻り値の仕様や例外挙動等）したい場合は、対象モジュール／関数を指定してください。