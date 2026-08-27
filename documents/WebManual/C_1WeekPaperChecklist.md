# C. 1 Week Paper 運用チェックリスト

- **対象**: `KABUSYS_ENV=paper_trading` で、実資金を使わずに 1 week 回す前後の確認
- **目的**: `Core` の日次運用フローが安定して回るかを、実運用に近い形で確認する
- **前提**: [C_PaperTrading.md](./C_PaperTrading.md) の準備が完了している

---

## C-1. この 1 week で確認すること

このチェックでは、次の 4 点を見る。

- 毎朝の `Pre-Market -> Execution -> Monitoring` が安定して回るか
- 引け後の `Market Close -> Performance` が安定して回るか
- `paper_trading.db` と `monitoring.db` に異常が出ないか
- 1 week 後に `paper_verification_report` の基準を満たすか

この期間は `live` へ進まず、まず `paper_trading` の記録を揃えることを優先する。

---

## C-2. 開始前チェック

### 必須

- [ ] `python scripts/setup_db.py --paper` 実行済み
- [ ] `.env` に `KABUSYS_ENV=paper_trading` を設定済み
- [ ] `python -m kabusys.validate_config` が致命エラーなし
- [ ] `data/paper_trading.db` が存在する
- [ ] DuckDB に直近営業日の `prices_daily` / `features` / `signals` が入っている
- [ ] `signal_queue` に翌営業日の `pending` シグナルがある

### 推奨

- [ ] `PAPER_TRADING_INITIAL_CASH` を実際に想定する運用資金に近い値へ寄せる
- [ ] 最初は `Pure Mock` で開始する
- [ ] API 経路も見たい場合だけ `KABU_USE_SANDBOX=true` を使う

---

## C-3. 毎朝の手順

### 08:00 前後

```powershell
python -m kabusys.run_pre_market_report --save
python -m kabusys.run_signal_queue_report
python -m kabusys.run_position_reconciliation_report
```

確認項目:

- [ ] `Pre-Market Report` が `BLOCKED` でない
- [ ] `signal_queue` に `pending` がある
- [ ] `data/stop_requested.flag` が残っていない
- [ ] 前日からのポジション復元に違和感がない

### 08:30 前後

```powershell
python scripts/start_system.py --dry-run
python scripts/start_system.py --component execution
```

確認項目:

- [ ] `run_execution` が起動エラーなく立ち上がる
- [ ] `artifacts/execution_startup/{date}/report.md` が保存される
- [ ] `data/execution.pid` が作成される
- [ ] `orders_no_status` や `position_discrepancies` が異常値でない

### 09:00 前後

```powershell
python scripts/start_system.py --component monitoring
```

確認項目:

- [ ] `data/monitoring.pid` が作成される
- [ ] Streamlit または `run_intraday_monitor --watch` で監視できる
- [ ] `system_status` / `risk_logs` / `trade_logs` が増えている

---

## C-4. 日中の確認

見るもの:

- `Home`
- `Signal Queue`
- `Performance`

確認項目:

- [ ] `Kill Switch` が意図せず有効化されていない
- [ ] `ORDER_ERROR` / `RISK_BREACH` / `CRITICAL` が連発していない
- [ ] 送信済み注文が異常に滞留していない
- [ ] `paper_trading.db` に注文・約定が記録されている

必要なら:

```powershell
python -m kabusys.run_intraday_monitor --watch
Get-Content logs\execution.log -Tail 50
Select-String -Path logs\*.log -Pattern "ERROR|CRITICAL"
```

---

## C-5. 引け後の手順

```powershell
python -m kabusys.run_market_close_report --save
python -m kabusys.run_performance_report --type daily --env paper_trading --save
```

確認項目:

- [ ] `Market Close Report` が保存される
- [ ] `paper_trading` 日次 performance が出る
- [ ] `positions` と `portfolio_performance` が更新される
- [ ] 明日向け `signal_queue` が生成される

補足:

- `night_batch_report` は実装済みだが、自動接続の運用確認は別途見る
- 1 week の試験運用では、`signal_queue` が翌営業日分まで出ていることを毎日確認する

---

## C-6. 毎日止める前の確認

- [ ] `execution` と `monitoring` を正常停止できる
- [ ] `paper_trading.db` が壊れていない
- [ ] 翌朝に再起動してもポジションが復元される見込みがある

停止:

```powershell
python scripts/stop_system.py
```

---

## C-7. 1 week 終了後の確認

### Paper Verification

```powershell
python -m kabusys.tools.paper_verification_report --from 2026-05-11 --to 2026-05-15
```

見る基準:

- 稼働率 `>= 99%`
- 注文成功率 `>= 90%`
- 送信率 `>= 95%`
- P95 レイテンシ `<= 200ms`

これらの閾値は [paper_verification_report.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/tools/paper_verification_report.py:25) に実装されている。

### Performance

```powershell
python -m kabusys.run_performance_report --type weekly --env paper_trading --save
```

見るもの:

- 週次損益
- 連続エラーの有無
- ドローダウン
- 約定や送信の偏り

---

## C-8. live へ進まない条件

次のいずれかがあれば、まだ `live` へ進まない。

- `paper_verification_report` が基準未達
- `Pre-Market` や `Execution Startup` で日次エラーが繰り返される
- `position reconciliation` に継続的な不整合がある
- `signal_queue` の生成が営業日ベースで安定しない
- 手動復旧が毎日必要になる

---

## C-9. 実装上の不足・注意点

現状のコード上で注意すべき点は次。

- `paper_verification_report` の基準判定はあるが、未達時に `live` 起動を自動ブロックする仕組みは見当たらない
- `night_batch_report` は CLI はあるが、自動接続の運用確認は別途必要
- `Addon` 系はこの 1 week の必須対象ではない。最初は `Core` 導線だけで回す方がよい

---

## C-10. 関連

- [C_PaperTrading.md](./C_PaperTrading.md)
- [W1_08 Paper Trading 4週間検証 Runbook](../08_Operations/W1_08_PaperTradingValidationRunbook.md)
- [D_LiveOperation.md](./D_LiveOperation.md)
- [documents/08_Operations/TradingRunbook.md](../08_Operations/TradingRunbook.md)
- [documents/08_Operations/Monitoring.md](../08_Operations/Monitoring.md)
