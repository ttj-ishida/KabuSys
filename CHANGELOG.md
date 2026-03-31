# CHANGELOG

すべての重要な変更点はこのファイルに記録します。フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）に準拠します。

なお、本リポジトリのバージョンは `src/kabusys/__init__.py` の __version__ = "0.1.0" に合わせています。

## [Unreleased]
- 次回リリースに向けた変更点をここに記載します。

## [0.1.0] - 2026-03-31
初回公開リリース。

### Added
- パッケージ基本情報
  - kabusys パッケージの初期バージョン（0.1.0）。公開モジュール: data, research, ai, config, etc.

- 環境設定・ロード機能（kabusys.config）
  - .env ファイルまたは環境変数からの設定読み込みを実装。
  - プロジェクトルートの自動探索: `.git` または `pyproject.toml` を基準に探索し、パッケージ配布後でも CWD に依存しない動作を目指す。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env のパース機能:
    - export 形式対応（`export KEY=val`）。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - インラインコメント判定（クォートなしでは `#` の直前がスペース/タブならコメント扱い）。
  - 上書き制御:
    - `override` と `protected` により OS 環境変数を保護する仕組みを提供。
  - 必須環境変数取得ヘルパー `_require` と Settings クラスを提供。
    - J-Quants / kabu ステーション / Slack / DB パス等のプロパティを含む。
    - `KABUSYS_ENV` と `LOG_LEVEL` のバリデーション（許容値列挙）を実装。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news テーブルのニュースを LLM（gpt-4o-mini）でセンチメント解析し、銘柄ごとの ai_scores に書き込む機能を実装。
  - タイムウィンドウ定義（JST ベースの前日 15:00 ～ 当日 08:30）と Unix/UTC 変換ヘルパー calc_news_window を提供。
  - 処理フロー:
    - 銘柄ごとに最新記事を集約し（最大記事数、最大文字数でトリム）、最大 20 銘柄/チャンクでバッチ送信。
    - OpenAI JSON mode を利用し厳密な JSON 応答を期待。
    - 429（レート制限）・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。
    - レスポンスのバリデーションとスコアのクリッピング（±1.0）。
    - DuckDB 互換性（executemany に空リストを渡さない制約）を考慮して部分的に DELETE → INSERT の冪等的書き込みを実装。
  - テスト用フック:
    - `_call_openai_api` を patch してモック化可能（ユニットテスト容易化）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（Nikkei225 連動型）の 200 日移動平均乖離（重み 70%）とニュースベースのマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込みする機能を実装。
  - 処理フロー:
    - ma200_ratio の算出（target_date 未満のデータのみ使用、ルックアヘッド防止）。
    - マクロキーワードでフィルタしたニュースタイトルを収集し、LLM（gpt-4o-mini）でマクロセンチメントを評価。
    - API 失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - レジームスコアはクリップされ、閾値に基づきラベル付け。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT により冪等に実施し、失敗時は ROLLBACK。
  - OpenAI 呼び出しはニュースNLP側と独立した実装（モジュール結合を避ける設計）。

- データプラットフォーム（kabusys.data）
  - ETL 構成要素:
    - pipeline モジュールと ETLResult データクラス（kabusys.data.pipeline.ETLResult）を公開。etL 実行のメタ情報（取得数、保存数、品質問題、エラー等）を保持。
    - ETL に関するユーティリティ（差分取得、バックフィル、品質チェックの受け皿）を実装（設計に基づく）。
  - カレンダー管理（kabusys.data.calendar_management）:
    - JPX カレンダーの夜間バッチ更新 job（calendar_update_job）を実装。J-Quants API からの差分取得 → market_calendar テーブルへの冪等保存を行う。
    - 営業日判定・前後営業日取得・期間内営業日リスト・SQ 判定などのユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - カレンダーデータ未取得時の曜日ベース・フォールバックや、DB にある値を優先する一貫した動作を実装。
    - 最大探索範囲や健全性チェック（将来日付が過度に先の場合はスキップ）を導入。
    - J-Quants クライアント呼び出し部分は jquants_client モジュールを利用する設計（抽象化）。

- リサーチモジュール（kabusys.research）
  - factor_research モジュール:
    - Momentum (1M/3M/6M リターン、200 日 MA 乖離)、Volatility (20 日 ATR 等)、Value (PER, ROE) を DuckDB の prices_daily / raw_financials を参照して計算する関数を提供（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 扱い、結果は (date, code) を含む dict リストで返す。
  - feature_exploration モジュール:
    - 将来リターン算出（calc_forward_returns）: 複数ホライズンに対応、ホライズンのバリデーションあり。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装（同順位は平均ランクで扱う）。
    - ランク変換ユーティリティ（rank）およびファクター統計サマリー（factor_summary）を実装。
  - これらは標準ライブラリと DuckDB のみで動作する設計で、外部 API や取引システムにはアクセスしない。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

### Notes / 設計上の重要事項
- ルックアヘッドバイアス防止:
  - すべての時刻・日付計算で内部的に date.today() / datetime.today() を直接参照しない方針を採用。関数に target_date を明示的に渡すことで過去データのみを参照するよう実装。
- フェイルセーフ:
  - LLM 呼び出し失敗時は致命例外を送出せず（score_news/score_regime は API 未応答時にスキップや 0.0 フォールバック）、ETL は部分失敗時も他データへの影響を最小化する設計。
- テスト容易性:
  - OpenAI API 呼び出しを行う内部関数（_call_openai_api）には patch 可能な実装を用意し、ユニットテストでのモックを想定。
- DuckDB 互換性:
  - DuckDB の executemany に空リストを渡せない制約を考慮して、INSERT/DELETE 実行前に空リストチェックを実施。
- OpenAI モデル/モード:
  - gpt-4o-mini を利用、JSON Mode（response_format={"type": "json_object"}）で厳密 JSON 出力を期待する実装。

以上が初回リリース（0.1.0）の主要な追加内容と設計上の要点です。必要であれば、各モジュールごとの公開 API（関数・クラス名と簡単な使用例）や、環境変数一覧（.env.example 相当）の追記も作成します。必要であれば指示してください。