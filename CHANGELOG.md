# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
本ファイルはコードベースから推測して自動生成したもので、実装内容の要約を含みます。

すべてのバージョンはセマンティックバージョニングに従います。

## [Unreleased]

（現状のコードはバージョン 0.1.0 としてリリースされているため、Unreleased に未確定の差分はありません）

## [0.1.0] - 2026-03-31

初回公開リリース。本バージョンでは日本株自動売買プラットフォーム「KabuSys」のコア機能（データ基盤・研究用ユーティリティ・AI ベースのニュース解析・環境設定等）が実装されています。

### Added
- パッケージ基本情報
  - パッケージのトップレベル定義を追加（src/kabusys/__init__.py）。バージョンは `0.1.0`。
  - エクスポート対象モジュール: data, strategy, execution, monitoring（__all__ にて宣言）。

- 環境変数／設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml を基準）により CWD に依存しない探索を提供。
  - .env と .env.local の優先順位を考慮した読み込み（OS 環境変数は保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能を追加（テストで利用可能）。
  - .env パーサの強化:
    - コメント、export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープなどに対応。
    - インラインコメントの扱いと無効行のスキップ。
  - Settings クラスを提供し、アプリケーションで使用する主要設定値（J-Quants トークン、kabu API 設定、Slack トークン/チャンネル、DB パス、監視閾値、環境 / ログレベル判定など）をプロパティ経由で取得可能。
  - 環境変数の必須チェック（_require）により未設定時は明示的にエラーを発生。

- AI モジュール（src/kabusys/ai/）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を基に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントを算出。
    - バッチサイズや記事数・文字数の上限（トークン肥大対策）を設計に反映（チャンク処理, _BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装。致命的なAPI失敗は該当チャンクをスキップして処理継続するフェイルセーフ動作。
    - レスポンスの厳密なバリデーション機構（JSON 抽出、results リストの検査、コード整合性、数値バリデーション、±1.0 でのクリップ）。
    - DuckDB への書き込みは部分置換（該当コードのみ DELETE → INSERT）で冪等性と部分失敗時の保護を実現。
    - テスト容易性のため OpenAI 呼び出し部分を内部関数化し、ユニットテストで差し替え可能。
    - calc_news_window 関数により JST のニュース収集ウィンドウ（前日 15:00 ～ 当日 08:30）を UTC 相対で算出。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算におけるルックアヘッド防止（target_date 未満のみ参照）、データ不足時のフォールバック（中立 1.0）を実装。
    - マクロニュースの抽出（マクロキーワード群によるフィルタリング）と LLM 呼び出し（gpt-4o-mini）による macro_sentiment 評価を実装。API 失敗時は macro_sentiment=0.0 として継続するフェイルセーフ。
    - OpenAI 呼び出しのリトライ／バックオフ処理、レスポンスパースの安全化、及び idempotent な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - LLM 呼び出し箇所は news_nlp と独立した実装にしてモジュール結合を避ける設計。

- データ基盤（src/kabusys/data/）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを用いた営業日判定・次/前営業日取得・期間内営業日取得・SQ日判定ロジックを実装。
    - DB にカレンダーがない／未登録日の場合は曜日（土日）ベースのフォールバックを利用。
    - カレンダー更新ジョブ（calendar_update_job）を実装：J-Quants から差分取得 → save_market_calendar 経由で冪等保存、バックフィルや健全性チェックを備える。
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを追加し、ETL 実行統計（取得件数・保存件数・品質問題・エラー）を保持・辞書化するユーティリティを提供。
    - 差分更新、backfill、品質チェックの設計方針を実装対象として取り込む構成（jquants_client と quality モジュールとの連携を想定）。
    - etl モジュールは pipeline.ETLResult を再エクスポートして公開 API を整理。

- 研究／リサーチユーティリティ（src/kabusys/research/）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - ファクター計算を実装（Momentum/Value/Volatility/Liquidity）:
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日 MA 乖離率）。
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率など。
      - calc_value: PER（EPS に依存、欠損時は None）、ROE（raw_financials からの取得）。
    - DuckDB 上の SQL ウィンドウ関数を活用し、営業日ベースのホライズンとスキャン範囲を考慮した実装。
    - 実行は常に価格・財務テーブルのみ参照し、本番口座や注文 API にはアクセスしない設計。
    - zscore_normalize を外部（kabusys.data.stats）から利用可能にするエクスポートを想定。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン算出（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）で LEAD を使ったリターン計算。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装し、データ不足時は None を返す。
    - rank/ factor_summary: ランク変換（平均ランク、同順位の平均処理）および基本統計量（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB のみで完結するよう実装。

- テスト・運用上の配慮
  - OpenAI 呼び出し箇所（news_nlp, regime_detector）で内部関数化し、unittest.mock で差し替え可能にして単体テストを容易化。
  - API キーは関数引数経由で注入可能（api_key 引数）でテスト可能性を向上。
  - DuckDB に対する executemany の空リスト回避、部分置換（コード絞り込み）など DuckDB 特性に基づく互換性対策を実装。
  - ロギングを多用し、警告・エラー発生時に詳細状況を残す設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし。ただし多くのフェイルセーフ／入力検証を実装し、実運用での失敗耐性を強化）

### Security
- OpenAI API キーは環境変数（OPENAI_API_KEY）または関数引数で扱い、明示的に必須チェックを行うことで誤設定を早期検出する設計。

---

注記:
- 本 CHANGELOG はソースコードから推察して作成した要約であり、実際のコミット履歴やイシュー番号は含みません。リリースノートとして利用する場合は、実リポジトリのコミット・PR 情報やテスト結果を参照して補足してください。