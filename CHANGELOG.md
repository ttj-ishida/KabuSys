Keep a Changelog に準拠した形式で、このコードベースから推測できる変更履歴（日本語）を作成しました。

注: リリース日や細かい文言はコード内容からの推測です。必要に応じて日付・文言を調整してください。

# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-28
初期リリース — 基本的なデータ基盤、調査（Research）、AI ベースのニュース解析・市場レジーム判定、および環境設定ユーティリティを実装。

### Added
- パッケージ基盤
  - パッケージバージョンを設定（kabusys.__version__ = "0.1.0"）。
  - 主要サブパッケージを __all__ で公開: data, strategy, execution, monitoring。

- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数からの設定自動読み込みを実装。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を起点に探索（CWD 非依存）。
  - .env パーサーを強化:
    - export KEY=val 形式サポート。
    - シングル／ダブルクォート内でのバックスラッシュエスケープ処理。
    - クォートなし値でのインラインコメント判定（直前が空白・タブの場合のみ # をコメントと扱う）。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。OS の既存キーは protected として保護。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須取得ヘルパー _require と Settings クラスを提供（各種必須トークン・パス・ログレベル・環境区分をプロパティ化）。
  - 設定値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）および is_live / is_paper / is_dev のショートカット。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini）へ JSON モードでバッチ送信してセンチメントを算出。
    - タイムウィンドウ計算（JST ベース → DB 比較は UTC naive datetime）を実装（calc_news_window）。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、各銘柄は最新 10 記事・最大 3000 文字にトリム。
    - 再試行戦略（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）。
    - レスポンス検証と堅牢な JSON パース（前後の余計なテキストを除去するフォールバック含む）。
    - 結果を ai_scores テーブルへ冪等に書き戻す（DELETE → INSERT）。部分失敗時に既存スコアを保護する設計。
    - テスト支援: OpenAI 呼び出しを置換可能（_unittest.mock.patch 用の内部関数 _call_openai_api）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（ウエイト 70%）とマクロニュース由来の LLM センチメント（ウエイト 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出。
    - LLM 呼び出しは gpt-4o-mini の JSON mode を利用。応答 JSON の堅牢なパースとリトライ処理を実装。
    - マクロキーワードによる raw_news フィルタリング（最大 20 記事）。
    - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時に ROLLBACK）。
    - API 失敗時は macro_sentiment を 0.0 としてフォールバックするフェイルセーフ設計。
    - テスト支援: _call_openai_api を差し替え可能（モジュール間で private を共有しない設計）。

- Data モジュール（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定ユーティリティ群を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末除外）を採用。
    - next/prev/get の実装は DB 登録値を優先し、未登録日は曜日ベースで一貫性を保つ。
    - カレンダー差分フェッチと夜間更新ジョブ calendar_update_job を実装（J-Quants API 経由で差分取得 → 保存）。バックフィルと健全性チェックあり。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - 差分更新、保存（jquants_client の idempotent save_* ）、品質チェックを統合する ETL の枠組み。
    - ETLResult dataclass を導入（取得数・保存数・品質問題・エラーの集約）。
    - 各種内部ユーティリティ: テーブル存在チェック、最大日付取得、取得範囲の調整（トレーディングデイ調整）等。
    - backfill のデフォルト値やカレンダールックアヘッド設定を実装。
    - DuckDB のバージョン差分（executemany の空リスト不可など）に配慮した実装注記。
  - ETL の公開インターフェース etl.py で ETLResult を再エクスポート。

- Research モジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、
      流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB SQL で計算する関数を実装:
      - calc_momentum, calc_volatility, calc_value
    - データ不足時の None 扱いや行ウィンドウ処理に配慮。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns：任意ホライズンに対応、入力検証あり）。
    - IC（Information Coefficient）計算（calc_ic：Spearman ランク相関を手実装）。
    - ランク変換ユーティリティ（rank：同順位は平均ランク）。
    - 統計サマリー（factor_summary：count/mean/std/min/max/median を算出）。
    - pandas 等に依存せず標準ライブラリと DuckDB のみで実装。

- テスト・運用上の配慮
  - OpenAI 呼び出し部分を patch してテストしやすい作りに（各 ai モジュール内の _call_openai_api を差替え可）。
  - API キー注入: 各関数は api_key 引数を受け取り、テスト時に環境変数を直接触らず検証可能。
  - DuckDB を想定し、SQL 実装で互換性の問題が出にくい形（row_number や window 関数等）で設計。

### Changed
- 初回リリースのため対象なし。

### Fixed
- 初回リリースのため対象なし。

### Security
- OpenAI API キーや各種トークンは Settings._require を通じて必須にし、環境変数による管理を想定。自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供しテスト時の誤動作を回避。

---

補足（設計上の注意点・既知の実装方針）
- ルックアヘッドバイアス防止: 多くの関数が内部で datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る設計になっています。
- DB 書き込みは冪等性に配慮（DELETE→INSERT、ON CONFLICT など）しており、部分失敗時に既存データを不必要に消さないように工夫されています。
- OpenAI への問い合わせは JSON モードを前提にしており、レスポンスのパースに堅牢性を持たせる実装が入っています（レスポンス前後のゴミテキスト処理など）。
- DuckDB のバージョン差異（executemany の空リスト問題など）を考慮した実装注記があります。

必要であれば各機能（例: news_nlp, regime_detector, calendar_update_job, ETLResult）について、より詳細な変更説明やリリースノート向けのスクリーンショット・使用例・リスク評価を追記します。