# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを使用します。

- ドキュメント化方針: 日付はリリース日を表します。未リリースの変更は `Unreleased` セクションに記載します。

## [Unreleased]
- なし（初回リリース以降の未公開変更はここに記載されます）。

## [0.1.0] - 2026-04-03
初期リリース。日本株自動売買プラットフォームのコアライブラリを実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（src/kabusys/__init__.py）。バージョンは `0.1.0`。
  - サブパッケージの公開インターフェースを定義（data, strategy, execution, monitoring）。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）を導入し、CWD に依存しない自動ロードを実現。
  - .env パーサ（シングル/ダブルクォート、エスケープ、export 先頭表記、インラインコメント処理をサポート）。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - 必須チェック用ヘルパー `_require` と Settings クラスを実装（J-Quants / kabu / LINE / DB /監視 やログ設定などのプロパティを提供）。
  - 環境値検証（KABUSYS_ENV / LOG_LEVEL のバリデーション）と利便性プロパティ（is_live / is_paper / is_dev）。

- AI 系（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を元に銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを算出。
    - 時間ウィンドウ定義（前日15:00 JST ～ 当日08:30 JST）を実装（calc_news_window）。
    - バッチ処理（1 コールあたり最大 20 銘柄）、トークン肥大化対策（記事数／文字数制限）を実装。
    - JSON mode を利用したレスポンス処理、厳格なバリデーションとスコアの ±1.0 クリップ。
    - 再試行（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフ実装。致命的でないエラー時はスキップして継続するフェイルセーフ設計。
    - DuckDB への冪等書き込み（DELETE → INSERT、トランザクション管理）と部分失敗時の既存データ保護。
    - 公開 API: score_news(conn, target_date, api_key=None) — 書き込み件数を返す。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - ma200 比率計算（ルックアヘッド防止のため target_date 未満のみ使用）、マクロニュース抽出、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API 呼び出しは失敗時に macro_sentiment=0.0 として継続する（フェイルセーフ）。再試行・エラー区別の実装あり。
    - 公開 API: score_regime(conn, target_date, api_key=None) — 成功時に 1 を返す。

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定 API を提供（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - DB データがない場合は曜日ベースでフォールバック（週末は休場）。
    - 夜間バッチ更新関数 calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存）。
    - 最大探索日数やバックフィル日数等の安全策を導入。

  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETL 実行結果を表す dataclass ETLResult を追加（取得件数 / 保存件数 / 品質問題 / エラー集約）。
    - 差分更新、品質チェック、バックフィルなどの方針を実装。jquants_client と quality モジュールとの連携を想定。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum: 1M/3M/6M リターン計算、200 日移動平均乖離（ma200_dev）。データ不足時は None を返却。
    - Volatility / Liquidity: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - Value: raw_financials からの EPS/ROE と価格を組み合わせて PER/ROE を算出（EPS が 0/欠損なら None）。
    - DuckDB 上の SQL ウィンドウ関数を活用した実装。外部サービスへはアクセスしない安全設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズンでのリターンを一括取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関を実装。サンプル不足時は None。
    - ランキング（rank）関数: 同順位は平均ランクで処理。丸めによる ties の扱いを工夫。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。
  - research パッケージの公開 API を整備（__init__.py）で主要関数をエクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーの取り扱いは api_key 引数または環境変数 OPENAI_API_KEY を使用。環境変数未設定時は明示的にエラーを返すことで誤用を防止。

### Notes / 設計上の重要ポイント
- ルックアヘッドバイアス対策: 全ての外部時刻参照やデータ取得ロジックは target_date ベースで計算し、datetime.today()/date.today() による暗黙の参照を避ける設計になっています（AI スコアリング・レジーム判定・ファクター計算など）。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）呼び出しに失敗した際は例外を必ず上位に伝播させるのではなく、各モジュールで適切にフォールバック（0.0 やスキップ）する方針を採用し、ETL/バッチ処理全体の連続性を重視しています。
- DuckDB を主要な分析 DB として利用。トランザクション制御（BEGIN/COMMIT/ROLLBACK）や executemany の互換性を考慮した実装となっています。
- テスト容易性: OpenAI 呼び出し部分は内部関数で抽象化しており、unittest.mock.patch による差し替えが想定されています（単体テストのためのフックを用意）。

### Known limitations / 今後の改善候補
- news_nlp の出力バリデーションは堅牢に作られているが、LLM の予期せぬ出力に対するさらなるガード（レスポンス規模・型・重複コードの扱いなど）で改良の余地あり。
- ETL の詳細（差分算出ロジック、quality モジュールの各チェック項目）はインテグレーション運用でチューニングが必要。
- research モジュールは pandas 等に依存せず軽量に実装しているが、大規模データでのパフォーマンス評価・最適化が今後の課題。

---

この CHANGELOG はコードベース（src/ 以下）の内容から推測して作成しています。追加の実装・リリースが行われた場合は本ファイルを更新してください。