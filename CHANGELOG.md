# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0

## [0.1.0] - 2026-04-04
初回リリース

### Added
- パッケージ基本情報
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ で定義。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動ロードする機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索して行うため、CWD に依存しない。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
  - .env パーサの実装:
    - 空行・コメント（#）、export KEY=val 形式に対応。
    - シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱いを考慮。
  - 環境設定取得用 Settings クラスを提供:
    - J-Quants / kabu API / LINE / DB パス / 監視パラメータ / システムモード等のプロパティを用意。
    - 必須環境変数未設定時は _require() が ValueError を送出。
    - KABUSYS_ENV と LOG_LEVEL の妥当性チェック（許容値の検証）。
    - Path 型のプロパティは expanduser を適用。

- AI（NLP）機能（src/kabusys/ai/）
  - ニュースセンチメント分析（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄単位に記事をまとめ、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - JST 時間ウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST）とそれに基づく DB クエリを実装（calc_news_window）。
    - バッチ処理: 最大 20 銘柄/コール、1 銘柄あたり最大記事数・文字数でトリム。
    - JSON Mode のレスポンスを厳密に検証（results 配列、code/score 構造、スコアの数値性、未知コード無視）。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。フェイルセーフとして API 失敗時は該当チャンクをスキップ。
    - DuckDB への書き込みは冪等に実行（該当コードを DELETE → INSERT）し、部分失敗時に既存スコアを保護。
    - テスト容易性: OpenAI 呼び出し箇所は _call_openai_api を通すためモック差替えが可能。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - prices_daily からのデータ取得にルックアヘッド排除（target_date 未満のみ）を徹底。
    - マクロニュース抽出はキーワードベース（複数キーワード）でタイトルを抽出し、OpenAI（gpt-4o-mini）へ送信。
    - API 呼び出しのリトライ（RateLimit/接続/タイムアウト/5xx）とエラー時のフェイルセーフ（macro_sentiment=0.0）。
    - 結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）する実装。
    - テスト容易性: _call_openai_api を差し替え可能。

- データ（DataPlatform）機能（src/kabusys/data/）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを参照して営業日判定・次/前営業日取得・期間内営業日取得・SQ 日判定のユーティリティを提供。
    - DB にデータがある場合は DB 値を優先、未登録日は曜日ベース（平日かどうか）をフォールバックとして一貫性を確保。
    - 夜間バッチ更新 job (calendar_update_job) を実装: J-Quants から差分取得→保存（バックフィル・健全性チェック含む）。
    - 最大探索日数やバックフィル日数等の安全ガードを実装して無限ループや異常値を防止。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを実装し、ETL の実行結果（取得数・保存数・品質問題・エラー）を集約可能。
    - 差分更新・バックフィル・品質チェックの方針を実装設計に反映。
    - ETLResult の dict 変換で品質問題をシリアライズ可能。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

- 研究用ユーティリティ（src/kabusys/research/）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB を用いて計算する関数群を提供。
    - 入力は prices_daily / raw_financials のみ。出力は (date, code) をキーとした dict リスト。
    - データ不足時の扱い（必要行数未満で None を返す）を明示。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（営業日）ごとのリターンを一度のクエリで取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関によるファクター有効性評価（有効レコード 3 件未満で None を返す）。
    - ランキングユーティリティ（rank）: 同順位は平均ランクを割り当てる。
    - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
  - research パッケージは data.stats.zscore_normalize を再利用・公開。

### Notes / 実装上の重要な設計判断
- ルックアヘッドバイアス回避
  - AI モジュール、研究モジュール等はいずれも datetime.today()/date.today() を内部で参照せず、外部から渡された target_date に基づいて処理するよう設計（バックテスト再現性を重視）。

- DB 書き込みの冪等性
  - ai_scores、market_regime、market_calendar などへの書き込みは既存レコードを削除してから挿入する、あるいは ON CONFLICT による上書きの方針で冪等性を確保。

- フェイルセーフ / 部分成功許容
  - 外部 API（OpenAI、J-Quants）障害時は失敗した箇所のみをスキップして処理を継続する設計。ログに WARN/ERROR を出力しつつ、致命的でなければ処理全体を止めない。

- テスト容易性
  - OpenAI 呼び出しや外部依存の入り口を明確に分離（関数をモック可能に）し、ユニットテストで挙動を差し替えられるようにしている。

- 安全性・互換性
  - DuckDB の executemany に関する仕様差（空リスト問題）を回避するため、空チェックを行ってから executemany を呼ぶ実装とした。
  - OpenAI SDKの APIError で status_code がない場合にも対応する防御的実装を含む。

### Removed
- （該当なし）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 外部 API キーは引数経由または環境変数（OPENAI_API_KEY 等）を用いる。不要な漏洩を避けるためログにキーを出力しない実装方針。

---

（備考）
- 本 CHANGELOG はコードベースの実装内容から推測して作成しています。細かな挙動や API の戻り値に関する仕様は実際の実行環境・外部サービスのバージョンに依存するため、必要に応じて該当ソースの docstring や実装コメントを参照してください。