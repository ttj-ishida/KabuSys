# Changelog

すべての重要な変更点は Keep a Changelog の仕様に従って記載しています。  
日付は本コードベースの内容から推測したリリース日を使用しています。

## [Unreleased]

## [0.1.0] - 2026-04-01
初期リリース。以下の主要機能とモジュールを実装しました。

### Added
- パッケージ基盤
  - kabusys パッケージの公開インターフェースを定義（src/kabusys/__init__.py）。バージョンは 0.1.0。
  - モジュール公開: data, strategy, execution, monitoring を __all__ に追加。

- 環境変数・設定管理
  - .env / .env.local の自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルート検出（.git または pyproject.toml を起点）により CWD に依存しない自動ロード。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env のパースは export KEY=val 形式、クォート（シングル/ダブル）、エスケープ、インラインコメント（条件付き）等に対応。
    - .env と OS 環境変数の上書きポリシー（.env.local は上書き、.env は未設定時のみ設定）と保護キー処理を実装。
  - Settings クラスを提供し、アプリケーション設定をプロパティとして取得可能に（J-Quants／kabu API／Slack／データベースパス／監視閾値等）。環境変数未設定時は明確なエラーメッセージを投げる設計。

- AI 関連
  - ニュースセンチメント解析（銘柄単位）: score_news を実装（src/kabusys/ai/news_nlp.py）。
    - 時間ウィンドウ計算、raw_news と news_symbols の集約、1 銘柄あたりの記事数・文字数トリム、チャンク（最大 20 銘柄）での OpenAI バッチ呼び出しを実装。
    - gpt-4o-mini（JSON mode）を利用。429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンス検証・数値変換・±1.0 でのクリッピング・部分成功時の部分置換（DELETE → INSERT）を実装。
    - ルックアヘッドバイアス回避: datetime.today()/date.today() を参照しない設計。
  - 市場レジーム判定: score_regime を実装（src/kabusys/ai/regime_detector.py）。
    - ETF（1321）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出・保存。
    - raw_news のマクロキーワードフィルタ、OpenAI 呼び出し（gpt-4o-mini）、API リトライ、失敗時のフェイルセーフ（macro_sentiment=0.0）。
    - DuckDB へ冪等な書き込み（BEGIN/DELETE/INSERT/COMMIT）とロールバック処理。
  - AI モジュール単位でのテスト容易性を考慮し、OpenAI 呼び出し部分は差し替え可能（内部 _call_openai_api を patch で置き換え可能）。

- データ・ETL・カレンダー・パイプライン
  - ETL 結果を表現する ETLResult データクラスを追加（src/kabusys/data/pipeline.py）。
    - 取得件数・保存件数・品質問題・エラーログ等を包含し、辞書化（監査ログ用途）可能。
  - ETL の公開インターフェース再エクスポート（src/kabusys/data/etl.py）。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定 API を提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースのフォールバックで一貫した挙動。
    - calendar_update_job により J-Quants からの差分取得 → 冪等保存（save_market_calendar 経由）を実装。バックフィル、健全性チェックあり。
  - DuckDB を主要な永続層として利用し、SQL ウィンドウ関数等を活用した効率的な集計実装。
  - DB 書き込みは部分失敗時の既存データ保護を考慮（対象コードを限定した DELETE → INSERT を使用）。

- リサーチ／ファクター計算
  - ファクター計算群を実装（src/kabusys/research/*）。
    - calc_momentum: 1M/3M/6M リターン・200 日 MA 乖離（prices_daily を使用）。
    - calc_volatility: 20 日 ATR, 相対 ATR, 20 日平均売買代金, 出来高比率。
    - calc_value: PER / ROE（raw_financials から最新財務を取得して計算）。
    - calc_forward_returns: 与えられたホライズンに対する将来リターン（複数ホライズン同時取得）。
    - calc_ic: ファクターと将来リターンのスピアマン（ランク）相関（IC）を計算。
    - rank, factor_summary, zscore_normalize（zscore は data.stats からの再利用を想定）。
  - 設計方針として外部 API や取引実行への影響を排除（リサーチのみで完結）、標準ライブラリ + DuckDB での実装を採用。

### Changed
- （初期リリースのため該当なし）

### Fixed
- .env パーサの堅牢化（引用符内のバックスラッシュエスケープ処理、コメント認識の改善、無効行スキップ等）を実装（src/kabusys/config.py）。
- OpenAI レスポンスのパース失敗や API エラー時にサービス全面停止とならないよう多数のフェイルセーフ（ログ出力してスキップ / 0.0 フォールバック）を導入（src/kabusys/ai/*）。

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- API キーは明示的に引数で注入可能（テスト性向上）かつ環境変数から取得する実装。未設定時は ValueError を投げて明示的に扱う。

---

主な設計方針（まとめ）
- ルックアヘッドバイアス防止: 内部実装で datetime.today()/date.today() に依存しない（すべて target_date ベースで動作）。
- フェイルセーフ性: 外部 API（OpenAI / J-Quants）失敗時は部分フェイルで継続し、ログとデフォルト値で動作を守る。
- 冪等性: DB 書き込みは冪等に設計（DELETE → INSERT、ON CONFLICT 想定の保存関数使用）。
- テスト容易性: OpenAI 呼び出し箇所等は差し替え可能に実装（内部関数 patch でモック可能）。

もし必要であれば、リリースノートをより粒度を細かく（ファイル単位・関数単位）に分けて出力します。どの形式で欲しいか指示してください。