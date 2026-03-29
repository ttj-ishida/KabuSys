# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
このファイルには、kabusys パッケージのリリース時に導入された主要な変更点・機能を日本語で記載しています。

## [0.1.0] - 2026-03-29

### 追加
- 初回公開リリース。パッケージの基本構成と主要サブモジュールを追加。
- パッケージ公開情報
  - パッケージバージョン: `0.1.0`
  - パッケージトップ: `src/kabusys/__init__.py`（__all__ に data, strategy, execution, monitoring を公開）

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込み。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - プロジェクトルート探索は __file__ を起点に `.git` または `pyproject.toml` を探索して判定（配布後も動作）。
  - 高度な .env パーサ実装:
    - `export KEY=val` 形式サポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなし行のインラインコメント取り扱い（直前がスペース/タブの場合のみ）
  - Settings クラスを提供（型付きプロパティ経由で設定取得）
    - J-Quants, kabuステーション, Slack, DB パス（DuckDB/SQLite）、環境（development/paper_trading/live）、ログレベル等のプロパティ
    - 必須設定は未設定時に ValueError を送出（例: OPENAI 用・Slack 用トークン類）
    - env/log_level 値検証を実装

- AI 関連（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとに OpenAI（gpt-4o-mini）でセンチメントを判定
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と比較）
    - バッチ処理（最大 20 銘柄 / リクエスト）、トークン肥大化対策（記事数上限・文字数上限）
    - 再試行ロジック（429/ネットワーク/タイムアウト/5xx）を実装（指数バックオフ）
    - レスポンスの厳格バリデーションと JSON 抽出ロジック（余分な前後テキストが混在するケースを想定）
    - スコアを ±1.0 にクリップ
    - 部分失敗を考慮した DB 書き込み（対象コードのみ DELETE → INSERT）で冪等性/部分失敗耐性を確保
    - テスト容易性のため OpenAI 呼び出し箇所はモック差し替え可能（_call_openai_api をパッチ可能）

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で 'bull' / 'neutral' / 'bear' を判定
    - マクロニュースは news_nlp の calc_news_window を使用して抽出
    - OpenAI 呼び出し（gpt-4o-mini）とリトライ/フェイルセーフ（API 失敗時は macro_sentiment=0.0）
    - レジームスコア合成後は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - ルックアヘッドバイアス対策を徹底（date < target_date 等）

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー（market_calendar）を扱うユーティリティを提供
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ロジック
    - DB 登録値を優先、未登録日は曜日ベースのフォールバック（堅牢な挙動）
    - 夜間バッチ更新 job（calendar_update_job）: J-Quants クライアント経由で差分取得 → 保存（バックフィル・健全性チェックあり）
    - 最大探索日数制限による無限ループ回避

  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult データクラスを公開（etl モジュールを通じて再エクスポート）
    - 差分取得・保存・品質チェックの概念実装
    - 最小データ開始日・バックフィル・カレンダー先読みなどのデフォルト設定
    - テーブル最大日取得ユーティリティ、テーブル存在チェック等
    - 保存処理の冪等性とエラー集約（quality チェックの結果は ETLResult に格納）

  - jquants_client / quality との連携想定（コード内でインポート/呼び出し）

- リサーチ / ファクター（src/kabusys/research）
  - factor_research.py
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）等の計算関数を実装
    - DuckDB SQL を利用した実装で外部 API に依存しない設計
    - データ不足時の扱い（None）を明示
  - feature_exploration.py
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）
    - IC（Spearman の ρ）計算、ランク変換ユーティリティ（同順位は平均ランク）
    - 統計サマリー（count/mean/std/min/max/median）
    - pandas 等に依存しない純標準ライブラリ実装

### 変更（設計/実装上の注記）
- OpenAI API 呼び出しは gpt-4o-mini を想定し、JSON Mode（response_format）で厳密 JSON 出力を期待するが、余分な前後テキストを想定して安全に抽出・復元する処理を実装。
- すべてのデータ処理関数は date/target_date を明示的に受け取り、datetime.today()/date.today() の直接参照を避けることでルックアヘッドバイアスを防止する設計を採用。
- DuckDB を主要なローカルデータストアとして使用。SQL クエリでウィンドウ関数（OVER）や LEAD/LAG を活用して計算。
- DB 書き込みは明示的なトランザクション（BEGIN/COMMIT/ROLLBACK）を利用し、例外時に ROLLBACK を試みる堅牢な実装。
- テスト容易性のため、OpenAI 呼び出し箇所や一部内部関数（例: _call_openai_api）を patch してモック化可能。

### 修正（既知の安全措置 / フェイルセーフ）
- OpenAI 呼び出しでのエラー（RateLimit, APITimeout, APIConnection 等）はリトライを行い、最終的に取得できない場合はフェイルセーフ値（macro_sentiment=0.0 やスキップ）で継続する実装。これにより外部 API 障害でパイプライン全体が停止しないようにしている。
- .env 読み込み時にファイル読み込み失敗が発生した場合は警告を出して処理を継続。

### 既知の制約 / 注意事項
- OpenAI API キー（api_key / 環境変数 OPENAI_API_KEY）が未設定だと、score_news / score_regime は ValueError を送出する。テストでは引数からキーを注入するか環境変数を設定する必要あり。
- DuckDB executemany に対する互換性注意: 空リストでの executemany は一部バージョンで制約があるため空チェックを行っている。
- news_nlp の出力は LLM に依存するため、モデルの応答フォーマットや品質により部分的にスコアが取得できないケースがある。取得できた銘柄のみを DB に書き込む設計。
- Calendar/ETL の一部は jquants_client / quality モジュールに依存（これらの具体的実装は外部）。

### 削除
- N/A（初回リリース）

### 非推奨
- N/A（初回リリース）

### セキュリティ
- セキュリティ関連の特記事項は現時点なし。ただし API キー・トークンは Settings 経由で環境変数で管理すること。

---

メモ:
- 本 CHANGELOG はコードベース（src/ 以下）から実装内容を抽出して記載しています。将来的なリリースではそれぞれの機能追加・修正・非互換変更に応じてエントリを追加してください。