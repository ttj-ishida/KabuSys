CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記録します。  
書式は「Keep a Changelog」に準拠しています。

Unreleased
----------

（今後の作業・既知の TODO）
- 監視・実行周りのモジュール（monitoring, execution）がパッケージ公開インターフェースに含まれているが、今回のコードベースでは実装が含まれていません。これらは次リリースで追加・ドキュメント化予定。
- jquants_client の実体は参照され利用されているが、外部実装依存のため接続性向上やエラーハンドリングの拡張を予定。
- テストカバレッジ強化（特に OpenAI 呼び出し回りの統合テスト、DuckDB 相互作用のモック化）。

0.1.0 - 2026-04-03
------------------

Added
- パッケージ初期公開。
  - パッケージ名: kabusys、バージョン: 0.1.0
  - __all__ に data, strategy, execution, monitoring を公開インターフェースとして定義。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）を実装し、CWD に依存しない自動 .env 読み込みを実現。
  - .env 解析の堅牢化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメント処理（クォート有無での扱い違い）を実装。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / システム環境（development/paper_trading/live）などをプロパティで取得。未設定の必須変数は明示的に例外を発生。
  - 環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL の許容値検証）。

- データ基盤関連 (kabusys.data)
  - ETL ユーティリティ公開インターフェース（ETLResult の再エクスポート）。
  - ETL パイプライン基盤 (kabusys.data.pipeline)
    - ETLResult dataclass を実装し、ETL 実行結果の構造化保存（取得数／保存数／品質問題／エラー等）。
    - 差分更新、バックフィル、品質チェックフローの設計を反映したユーティリティ関数群（内部ユーティリティ含む）。
    - DuckDB を前提としたテーブル存在確認や最大日付取得等の補助ロジック。
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーを管理する market_calendar テーブルの参照・更新ロジック。
    - 営業日判定（is_trading_day）、SQ判定（is_sq_day）、前後営業日取得（next_trading_day / prev_trading_day）、期間の営業日取得（get_trading_days）を実装。
    - calendar_update_job により J-Quants から差分取得し冪等に保存（バックフィル、健全性チェック含む）。
    - DB データがまばらな場合は曜日ベースのフォールバックを行い一貫性を保つ設計。

- 研究・ファクター計算 (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB 上の prices_daily / raw_financials から計算する関数を実装。
    - データ不足時は None を返す挙動を明確化。
    - SQL ウィンドウ関数を活用し、営業日スキャンレンジやバッファ（カレンダーバッファ）を考慮。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応、入力検証付き）。
    - IC（Information Coefficient）計算（ランク相関/Spearmanρ）と rank ユーティリティ（同順位は平均ランク）。
    - factor_summary による基本統計量（count/mean/std/min/max/median）計算。
  - research パッケージから主要関数群を再エクスポート（使いやすい API）。

- AI 支援機能 (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を銘柄ごとに集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を取得。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティを実装（calc_news_window）。
    - チャンクバッチ（最大 20 銘柄）での API 呼び出し、リトライ（429/ネットワーク/タイムアウト/5xx）を実装。戻り値のバリデーションとスコアのクリップを行う。
    - API 呼び出しはテスト時に差し替え可能（_call_openai_api を patch 可能）。
    - ai_scores への冪等的な書き込みロジック（該当 code の DELETE → INSERT）を実装し、部分失敗時に他銘柄の既存データを保護。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して、日次の市場レジーム（bull/neutral/bear）を算出し market_regime テーブルに書き込む関数を実装。
    - マクロ記事抽出（マクロキーワード群でフィルタ）→ OpenAI 呼び出し（JSON 出力想定）→ スコア合成 → 冪等 DB 書き込みのフローを実装。
    - ルックアヘッドバイアス回避のため日付参照手法に注意（datetime.today() 等を参照しない実装）。
    - API 障害時は macro_sentiment を 0 にフォールバックし継続するフェイルセーフ設計。
    - OpenAI クライアントエラーに対するリトライ/バックオフを実装。

- 共通実装・設計上の注意点
  - DuckDB をデータ層に採用し、SQL + Python の組み合わせで高性能に集計処理を実装。
  - API 呼び出し（OpenAI / J-Quants）に対して再試行・エラーハンドリング・フォールバックを備え、ETL/スコアリング処理の堅牢性を重視。
  - すべての「日付基準」の処理はルックアヘッドバイアス対策を施し、target_date を明示して計算するスタイル。
  - ロギングを適切に埋め込み、警告や情報を記録することで運用でのトラブルシュートを容易に。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- OpenAI API キーや各種シークレットは Settings を通して環境変数から取得する設計。必須変数未設定時は ValueError を送出して誤動作を防止。

Notes / 制約事項
- OpenAI 呼び出しには外部ネットワークアクセスと API キーが必要。キー未設定時は関連関数（score_news, score_regime）が ValueError を送出する。
- DuckDB のバージョン互換性に依存する箇所（executemany の空リスト扱い等）に配慮した実装が入っていますが、実稼働環境では DuckDB バージョンの検証を推奨します。
- 一部外部モジュール（jquants_client 等）は実装依存であり、接続先 API の仕様変更に伴い調整が必要になる可能性があります。
- news_nlp / regime_detector は LLM の JSON 出力に依存しており、レスポンス整形/パース失敗時はフェイルセーフとしてスコアをスキップまたは 0 にフォールバックします。

作者・貢献
- 初期実装: kabusys コードベース（src/kabusys 以下のモジュール群）

---

今後のリリースでは監視・実行モジュールの実装、フルエンドツーエンドの統合テスト、運用ドキュメント（デプロイ手順・環境変数一覧・推奨 DuckDB バージョン等）を追加予定です。必要であればこの CHANGELOG を英語版に翻訳することも可能です。