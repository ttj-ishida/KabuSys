# 初回セットアップ手順: J-Quants Bootstrap（一括データ投入）

- 対象: KabuSys の初回環境構築を行うユーザー
- 目的: J-Quants Bulk Download API から大量データを取得し、KabuSys の初期データ基盤を構築する
- 前提: 通常の日次差分更新ではなく、初回のみ（または環境再構築時）に行う作業である

---

## 1. この作業で何をするか

初回セットアップでは、J-Quants Bulk Download API から過去の株価・財務・銘柄マスタ・カレンダーを一括で DuckDB に投入します。

この作業の目的は次の通りです。

- バックテストに必要な過去データを揃える
- 実運用開始前の基礎データを揃える
- 通常運用の日次差分更新へ移行できる状態を作る

> ⚠️ Bulk Download API の利用には **J-Quants Standard プラン以上**が必要です。  
> Free / Light プランでは HTTP 403 が返るため、この手順は実行できません。

---

## 2. 前提条件

作業前に以下を確認してください。

- J-Quants Standard プラン以上を契約している
- `.env` に `JQUANTS_BULK_API_KEY` が設定されている（`python -m kabusys.config_setup` で設定）
- DuckDB のスキーマが初期化済みである（`python scripts/setup_db.py`）

---

## 3. Bootstrap の仕組み

```
J-Quants Bulk API
  GET /v2/bulk/list?endpoint=<ep>  → ファイルキー一覧（Key / Size / LastModified）
  GET /v2/bulk/get?key=<Key>       → presigned URL（有効期限5分）
      ↓ gzip CSV ダウンロード
  data/bootstrap/raw/<endpoint>/   ← ローカルキャッシュ（再実行時スキップ）
      ↓ parse & schema validation
  raw_prices / raw_financials / stocks / market_calendar / topix_daily
      ↓ ETL（NOT NULL / 型検証 → ON CONFLICT DO UPDATE）
  prices_daily / fundamentals
      ↓ 処理結果記録
  bootstrap_load_history           ← ファイル単位の処理状態（pending / loaded / failed）
```

### 取り込み対象エンドポイント

| Bulk エンドポイント         | 保存先テーブル          | 備考                      |
| --------------------------- | ----------------------- | ------------------------- |
| `/equities/bars/daily`      | `raw_prices`, `prices_daily` | AdjFactor を raw に保存 |
| `/equities/master`          | `stocks`                |                           |
| `/fins/summary`             | `raw_financials`, `fundamentals` |                  |
| `/markets/calendar`         | `market_calendar`       |                           |
| `/indices/bars/daily/topix` | `topix_daily`           | regime_detector が参照    |

---

## 4. 実行手順

### Step 1: ドライランで件数確認

```powershell
python -m kabusys.data.bootstrap --dry-run
```

ダウンロードせずにファイル件数のみ確認します。
API 接続が正常か、取得対象ファイル数が妥当かを事前に確認できます。

### Step 2: 一括取得を実行

```powershell
python -m kabusys.data.bootstrap
```

実行中は以下のように進捗が表示されます。

```
続きから実行します（ロード済みファイルはスキップ）。

[/equities/bars/daily] ファイル一覧を取得中...
[/equities/bars/daily] 42 ファイル検出
  [1/42] ダウンロード: equities_bars_daily_2024_01.csv.gz
  [1/42] ロード中: equities_bars_daily_2024_01.csv.gz
  [1/42] 完了: equities_bars_daily_2024_01.csv.gz (12,345 件)
  ...

Bootstrap 完了サマリー
  /equities/bars/daily         :    500,000 件
  /equities/master             :      4,000 件
  ...
```

### Step 3: 取込結果を確認

DuckDB で取り込みデータを確認します。

```powershell
duckdb data\kabusys.duckdb "SELECT MIN(date), MAX(date), COUNT(*) FROM prices_daily;"
duckdb data\kabusys.duckdb "SELECT COUNT(*) FROM stocks;"
duckdb data\kabusys.duckdb "SELECT COUNT(*) FROM fundamentals;"
duckdb data\kabusys.duckdb "SELECT MIN(date), MAX(date), COUNT(*) FROM market_calendar;"
duckdb data\kabusys.duckdb "SELECT MIN(date), MAX(date), COUNT(*) FROM topix_daily;"
```

### Step 4: Core フローの動作確認

Bootstrap 完了後、Core の処理フローが正しく動作するかを手動で確認します。

```powershell
python scripts\run_feature_gen.py
python scripts\run_strategy_signal.py
python scripts\run_portfolio_construction.py
```

---

## 5. 実行モードとオプション

### 続きから実行（デフォルト）

```powershell
python -m kabusys.data.bootstrap
```

`bootstrap_load_history` でロード済みのファイルをスキップするため、中断後の再実行が安全に行えます。

### 初期化して最初から実行

```powershell
# 確認プロンプトあり
python -m kabusys.data.bootstrap --fresh

# 確認スキップ（自動化・スクリプト用）
python -m kabusys.data.bootstrap --fresh --yes
```

`--fresh` は以下を実行します。

1. `bootstrap_load_history` テーブルを全削除
2. `data/bootstrap/raw/` 以下のダウンロード済みファイルを全削除
3. 最初からダウンロード・投入を再実行

### 特定エンドポイントのみ処理

```powershell
python -m kabusys.data.bootstrap --endpoint /equities/bars/daily
```

### 詳細ログ表示

```powershell
python -m kabusys.data.bootstrap --verbose
```

DEBUG レベルのログが出力されます。

---

## 6. 失敗・再実行時の対応

### 途中で中断した場合

再度 `python -m kabusys.data.bootstrap` を実行するだけで、`loaded` 済みファイルをスキップして続きから再開できます。

### 特定エンドポイントで失敗した場合

```powershell
python -m kabusys.data.bootstrap --endpoint /fins/summary
```

失敗したエンドポイントのみを再処理できます。

### 全て最初からやり直す場合

```powershell
python -m kabusys.data.bootstrap --fresh --yes
```

### `bootstrap_load_history` での状態確認

```powershell
duckdb data\kabusys.duckdb "SELECT endpoint, status, COUNT(*) FROM bootstrap_load_history GROUP BY endpoint, status;"
```

---

## 7. 通常運用への移行

Bootstrap 完了後は、通常運用では API ベースの日次差分更新へ移行します。

```powershell
python scripts\run_data_update.py
```

- Bootstrap は「土台作り」（初回のみ）
- 日次差分更新は「継続運用」（毎日自動実行）

この2つを混同しないでください。

---

## 8. チェックリスト

### 実行前

- [ ] J-Quants Standard プラン以上を契約している
- [ ] `python -m kabusys.validate_config` で `JQUANTS_BULK_API_KEY` が設定済みと表示される
- [ ] `python scripts/setup_db.py` で DuckDB スキーマが初期化済み
- [ ] `data/` ディレクトリに十分な空き容量がある

### Bootstrap 完了後

- [ ] `python -m kabusys.data.bootstrap` が正常終了している
- [ ] `prices_daily` に過去データが投入されている
- [ ] `stocks` に銘柄マスタが投入されている
- [ ] `fundamentals` に財務データが投入されている
- [ ] `market_calendar` にカレンダーが投入されている
- [ ] `topix_daily` に TOPIX データが投入されている
- [ ] `python scripts\run_feature_gen.py` が正常完了する
